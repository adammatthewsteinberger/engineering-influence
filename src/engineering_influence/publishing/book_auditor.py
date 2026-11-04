"""Audits a configured manuscript before any time is spent on typesetting."""

import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.chapter_opening_check import ChapterOpeningCheck
from engineering_influence.publishing.config_entries import ConfigEntries
from engineering_influence.publishing.entry import Entry
from engineering_influence.publishing.formula_check import FormulaCheck
from engineering_influence.publishing.issue_recorder import IssueRecorder
from engineering_influence.publishing.manuscript_text import ManuscriptText
from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.scaffold_check import ScaffoldCheck
from engineering_influence.publishing.source_inventory_check import SourceInventoryCheck
from engineering_influence.publishing.text_statistics import TextStatistics
from engineering_influence.publishing.threshold_check import ThresholdCheck


class BookAuditor:
    """Source-oriented gates: inventory, openings, scaffolding, depth, and apparatus.

    The audit makes the mechanical parts of editorial review visible. It does not decide
    whether a paragraph is beautiful or a claim is wise.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._relativizer = PathRelativizer(root)

    def audit(self, config_path: Path) -> AuditReport:
        """Return the audit report for one book config."""
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        source = self._root / config["source"]
        quality = config.get("quality", {})
        report = AuditReport(
            schema_version=1,
            slug=config_path.stem,
            config=self._relativizer.relative(config_path),
            source=self._relativizer.relative(source),
        )
        recorder = IssueRecorder(report, self._relativizer)
        configured = ConfigEntries().iterate(config)
        ignored = list(config.get("not_in_book", []))
        seen: set[str] = set()
        for kind, file, style, number in configured:
            if file in seen:
                recorder.record(
                    "error", "duplicate-file", f"{file} is listed more than once", source / file
                )
            seen.add(file)
            self._audit_entry(report, recorder, quality, source, kind, file, style, number)
        found = SourceInventoryCheck().run(
            recorder, source, [file for _, file, _, _ in configured], ignored
        )
        ThresholdCheck().run(report, recorder, quality, source, len(found), len(ignored))
        FormulaCheck().run(report, recorder, quality, source)
        report.finish()
        return report

    def _audit_entry(
        self,
        report: AuditReport,
        recorder: IssueRecorder,
        quality: dict[str, Any],
        source: Path,
        kind: str,
        file: str,
        style: str,
        number: int | None,
    ) -> None:
        path = source / file
        if not path.exists():
            recorder.record(
                "error", "missing-source", f"configured source file does not exist: {file}", path
            )
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            recorder.record("error", "unreadable-source", f"cannot read {file}: {exc}", path)
            return
        parsed = ManuscriptText().title_and_body(text)
        if parsed is None:
            recorder.record(
                "error", "missing-title", "the first line must be a level-1 Markdown title", path
            )
            return
        title, body = parsed
        if not title:
            recorder.record("error", "empty-title", "the reader-facing title is empty", path)
        if not body:
            recorder.record("error", "empty-entry", "the configured entry has no body", path)
        paragraphs = ManuscriptText().paragraphs(body)
        first = paragraphs[0] if paragraphs else ""
        words = TextStatistics().reader_words(body)
        report.entries.append(Entry(kind, file, title, style, number, words, first[:240]))
        if kind == "chapter":
            ChapterOpeningCheck().run(recorder, path, text, body, quality)
        ScaffoldCheck().run(recorder, path, text, body, quality)
