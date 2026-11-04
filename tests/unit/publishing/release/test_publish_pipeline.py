"""The publication pipeline's control flow, with fake build steps that make real artifacts."""

import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter

from engineering_influence.publishing.covers.cover_builder import CoverBuilder
from engineering_influence.publishing.epub.epub_builder import EpubBuilder
from engineering_influence.publishing.epub.epub_verifier import EpubVerifier
from engineering_influence.publishing.pdf_verifier import PdfVerifier
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.qa.page_record import PageRecord
from engineering_influence.publishing.qa.render_qa import RenderQa
from engineering_influence.publishing.qa.render_report import RenderReport
from engineering_influence.publishing.release.publish_pipeline import PublishPipeline
from engineering_influence.publishing.release.publish_steps import PublishSteps, Step
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_builder import BookBuilder

BASE = (
    'source = "src"\ntitle = "Demo"\nsubtitle = "Sub"\nauthor = "Ann Author"\npublisher = "P"\n'
    'edition = "First Edition"\nauthor_bio = "Bio."\ndescription = "d"\n'
)
PARTS = 'parts = [{ title = "One", chapters = ["one.md"] }]\n'

CONTRACT = """
[release]
required = true
keywords = ["a", "b", "c", "d", "e", "f", "g"]
minimum_description_words = 1
[release.pricing]
verified_on = "2099-01-01"
source_url = "https://example.com/p"
ebook = 5.99
paperback = 14.99
hardcover = 24.99
[release.formats]
kdp_hardcover = true
kdp_hardcover_max_pages = 1
"""


def project(root: Path, toml: str = BASE + PARTS) -> ProjectLayout:
    (root / "src").mkdir()
    (root / "src" / "one.md").write_text("# Chapter 1: One\n\nOne begins here.\n", encoding="utf-8")
    (root / "books").mkdir()
    (root / "books" / "demo.toml").write_text(toml, encoding="utf-8")
    return ProjectLayout(root)


def write_pdf(path: Path, pages: int = 3) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(432, 648)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)


def write_epub(path: Path, stored: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        kind = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
        z.writestr("mimetype", "application/epub+zip", compress_type=kind)


class FakeSteps(PublishSteps):
    """Creates the artifacts a healthy build would, unless told to fail or omit them."""

    def __init__(
        self,
        layout: ProjectLayout,
        fail: str | None = None,
        skip: tuple[str, ...] = (),
        pdf_pages: int = 3,
        bad_epub: bool = False,
    ) -> None:
        self.layout, self.fail, self.skip, self.pdf_pages, self.bad_epub = (
            layout,
            fail,
            skip,
            pdf_pages,
            bad_epub,
        )
        self.ran: list[str] = []

    def plan(self, slug: str, *, hardcover: bool) -> list[Step]:
        names = ["pdf", *(["hardcover"] if hardcover else []), "covers", "epub"]
        return [(n, [n, slug], self._action(n, slug)) for n in names]

    def _action(self, name: str, slug: str) -> Callable[[], str]:
        out = self.layout.output

        def run() -> str:
            self.ran.append(name)
            if name == self.fail:
                raise BookBuildError(f"{name} exploded")
            if name in self.skip:
                return "skipped"
            if name == "pdf":
                write_pdf(out / f"{slug}.pdf", self.pdf_pages)
            elif name == "hardcover":
                write_pdf(out / f"{slug}-hardcover.pdf", self.pdf_pages)
            elif name == "covers":
                for f in (
                    f"{slug}-ebook.jpg",
                    f"{slug}-paperback-wrap.pdf",
                    f"{slug}-hardcover-wrap.pdf",
                ):
                    (out / "covers" / slug).mkdir(parents=True, exist_ok=True)
                    (out / "covers" / slug / f).write_bytes(b"x")
            else:
                write_epub(out / f"{slug}.epub", stored=not self.bad_epub)
            return f"{name} ok"

        return run


class FakeQa(RenderQa):
    def __init__(self, blank_run: bool = False, error: Exception | None = None) -> None:
        self.blank_run, self.error, self.calls = blank_run, error, []

    def render(self, pdf: Path, output: Path, *, dpi: int = 90) -> RenderReport:
        self.calls.append((pdf.name, dpi))
        if self.error:
            raise self.error
        output.mkdir(parents=True, exist_ok=True)
        pages = [PageRecord(i, f"p{i}.png", 10, 10, 1, self.blank_run) for i in range(1, 4)]
        return RenderReport(1, pdf.name, str(output), dpi, 3, 3, [], pages)


CLOCK = iter(
    datetime(2031, 1, 1, tzinfo=UTC).replace(second=s % 60, minute=s // 60) for s in range(10_000)
)


def pipeline(
    layout: ProjectLayout, steps: PublishSteps, qa: RenderQa | None = None
) -> PublishPipeline:
    return PublishPipeline(layout, steps, qa=qa, clock=lambda: next(CLOCK))


def test_unknown_books_are_rejected(tmp_path: Path) -> None:
    layout = project(tmp_path)
    with pytest.raises(BookBuildError, match=r"no such book config: books/absent\.toml"):
        pipeline(layout, FakeSteps(layout)).publish("absent")


def test_a_failed_preflight_audit_stops_before_any_build(tmp_path: Path) -> None:
    layout = project(tmp_path)
    (tmp_path / "src" / "stray.md").write_text("# Stray\n\nx\n", encoding="utf-8")
    steps = FakeSteps(layout)
    result, ok = pipeline(layout, steps).publish("demo")
    assert not ok and result["status"] == "fail" and result["steps"] == [] and steps.ran == []
    assert result["manuscript_audit"]["issues"][0]["code"] == "unlisted-source"
    report = json.loads((tmp_path / "build/demo/release/publication-report.json").read_text())
    assert report["status"] == "fail" and report["human_review"]["status"] == "pending"
    assert next(a["kind"] for a in report["artifacts"]) == "pdf-interior"


def test_audit_only_runs_the_audits_and_nothing_else(tmp_path: Path) -> None:
    layout = project(tmp_path)
    steps = FakeSteps(layout)
    result, ok = pipeline(layout, steps).publish("demo", audit_only=True)
    assert ok and steps.ran == [] and result["release_readiness"]["status"] == "warning"
    assert (tmp_path / "build/demo/release/manuscript-audit.json").exists()
    assert list(result)[:12] == [
        "schema_version",
        "slug",
        "title",
        "formats",
        "config",
        "started_at",
        "git",
        "environment",
        "manuscript_audit",
        "release_readiness",
        "steps",
        "artifacts",
    ]


def test_a_full_run_without_rendering_records_everything(tmp_path: Path) -> None:
    layout = project(tmp_path)
    custom = tmp_path / "elsewhere" / "report.json"
    result, ok = pipeline(layout, FakeSteps(layout)).publish(
        "demo", no_render=True, report_path=custom
    )
    assert ok and result["status"] == "pass"
    assert [s["name"] for s in result["steps"]] == ["pdf", "covers", "epub"]
    assert result["visual_qa"] == {"status": "skipped", "reason": "--no-render"}
    assert (
        result["pdf"] == {"pages": 3} and "hardcover_pdf" not in result and "problems" not in result
    )
    assert all(a["exists"] for a in result["artifacts"])
    assert json.loads(custom.read_text())["status"] == "pass"
    assert (
        result["git"].keys() == {"commit", "branch", "status"} and "python" in result["environment"]
    )


def test_rendering_covers_both_variants_for_hardcover_books(tmp_path: Path) -> None:
    layout = project(tmp_path, BASE + PARTS + "[formats]\nhardcover = true\n")
    qa = FakeQa()
    result, ok = pipeline(layout, FakeSteps(layout), qa).publish("demo", dpi=72)
    assert ok and qa.calls == [("demo.pdf", 72), ("demo-hardcover.pdf", 72)]
    assert set(result["visual_qa"]) == {"paperback", "hardcover"}
    assert (tmp_path / "build/demo/visual-qa/hardcover/render-report.json").exists()
    assert [s["name"] for s in result["steps"]] == ["pdf", "hardcover", "covers", "epub"]
    assert result["hardcover_pdf"] == {"pages": 3}


def test_an_overlong_blank_run_fails_the_release(tmp_path: Path) -> None:
    layout = project(tmp_path)
    result, ok = pipeline(layout, FakeSteps(layout), FakeQa(blank_run=True)).publish("demo")
    assert (
        not ok
        and result["status"] == "fail"
        and result["visual_qa"]["paperback"]["unexpected_blank_pages"] == [1, 2, 3]
    )


def test_a_renderer_failure_is_recorded_not_raised(tmp_path: Path) -> None:
    layout = project(tmp_path)
    result, ok = pipeline(
        layout, FakeSteps(layout), FakeQa(error=BookBuildError("no renderer"))
    ).publish("demo")
    assert not ok and result["visual_qa"] == {"status": "fail", "error": "no renderer"}


def test_a_failing_step_stops_the_run_and_skips_rendering(tmp_path: Path) -> None:
    layout = project(tmp_path)
    steps = FakeSteps(layout, fail="covers")
    qa = FakeQa()
    result, ok = pipeline(layout, steps, qa).publish("demo")
    assert not ok and steps.ran == ["pdf", "covers"] and qa.calls == []
    assert result["visual_qa"] is None and result["steps"][1]["status"] == "fail"
    assert "covers exploded" in (tmp_path / "build/demo/release/covers.log").read_text()
    skipped, _ = pipeline(layout, FakeSteps(layout, fail="covers")).publish("demo", no_render=True)
    assert skipped["visual_qa"] == {"status": "skipped", "reason": "--no-render"}


def test_missing_artifacts_a_bad_epub_and_long_hardcovers_are_problems(tmp_path: Path) -> None:
    layout = project(
        tmp_path, BASE + PARTS + "[formats]\nhardcover = true\nhardcover_max_pages = 2\n"
    )
    result, ok = pipeline(layout, FakeSteps(layout, skip=("covers",), bad_epub=True)).publish(
        "demo", no_render=True
    )
    problems = result["problems"]
    assert not ok and any("missing artifact" in p and "ebook" in p for p in problems)
    assert "EPUB mimetype member must be uncompressed" in problems
    assert "hardcover interior has 3 pages; configured maximum is 2" in problems


def test_release_errors_that_need_the_pdf_fail_after_the_build(tmp_path: Path) -> None:
    # TOML needs top-level keys before tables, so the book structure precedes the contract.
    layout = project(tmp_path, BASE + PARTS + CONTRACT)
    result, ok = pipeline(layout, FakeSteps(layout)).publish("demo", no_render=True)
    codes = [f["code"] for f in result["release_readiness"]["findings"]]
    assert not ok and "hardcover-page-limit" in codes and result["status"] == "fail"
    assert result["release_readiness"]["pricing"]["page_count"] == 3


def test_strict_release_rejects_a_book_without_a_contract_at_preflight(tmp_path: Path) -> None:
    layout = project(tmp_path)
    steps = FakeSteps(layout)
    result, ok = pipeline(layout, steps).publish("demo", strict_release=True)
    assert not ok and steps.ran == []
    assert result["release_readiness"]["findings"][0]["code"] == "missing-release-contract"


def test_the_real_clock_and_default_renderer_are_used_when_not_injected(tmp_path: Path) -> None:
    layout = project(tmp_path)
    result, _ = PublishPipeline(layout, FakeSteps(layout)).publish("demo", audit_only=True)
    assert result["started_at"].endswith("+00:00")


class StubBuilder(BookBuilder):
    def __init__(self, layout: ProjectLayout) -> None:
        self.layout, self.calls = layout, []

    def build(self, slug: str, *, tex_only: bool = False, hardcover: bool = False) -> Path:
        self.calls.append(("hardcover" if hardcover else "pdf", slug))
        name = f"{slug}-hardcover.pdf" if hardcover else f"{slug}.pdf"
        path = self.layout.output / name
        write_pdf(path)
        return path


class StubCovers(CoverBuilder):
    def __init__(self, layout: ProjectLayout) -> None:
        self.layout, self.calls = layout, []

    def build(self, slug: str, preview: bool = False, hardcover_pdf: Path | None = None) -> Path:
        self.calls.append((slug, preview, hardcover_pdf))
        return self.layout.output / "covers" / slug


class StubEpub(EpubBuilder):
    def __init__(self, layout: ProjectLayout) -> None:
        self.layout = layout

    def build(self, slug: str, *, tex_only: bool = False) -> Path:
        path = self.layout.output / f"{slug}.epub"
        write_epub(path)
        return path


def real_steps(layout: ProjectLayout) -> tuple[PublishSteps, StubBuilder, StubCovers]:
    builder, covers = StubBuilder(layout), StubCovers(layout)
    return PublishSteps(layout, builder, covers, StubEpub(layout)), builder, covers


def test_the_step_plan_orders_the_builds(tmp_path: Path) -> None:
    steps, _, _ = real_steps(project(tmp_path))
    plain = steps.plan("demo", hardcover=False)
    assert [s[0] for s in plain] == ["pdf", "covers", "epub"]
    assert plain[1][1] == ["CoverBuilder.build", "demo", "--preview"]
    hard = steps.plan("demo", hardcover=True)
    assert [s[0] for s in hard] == ["pdf", "hardcover", "covers", "epub"]
    assert hard[2][1][-2:] == ["--hardcover-pdf", "output/demo-hardcover.pdf"]


def test_step_actions_build_and_verify(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    layout = project(tmp_path)
    steps, builder, covers = real_steps(layout)
    seen: list[Path] = []

    def pdf_ok(self: PdfVerifier, pdf: Path, config: Path, log: Path | None = None) -> list[str]:
        seen.append(log or Path())
        return []

    monkeypatch.setattr(PdfVerifier, "verify", pdf_ok)
    monkeypatch.setattr(EpubVerifier, "verify", lambda self, path, book: [])
    assert "built output/demo.pdf" in steps.pdf("demo")
    assert "built output/demo-hardcover.pdf" in steps.hardcover("demo")
    assert [p.parent.name for p in seen] == ["demo", "demo-hardcover"]
    assert "covers written to output/covers/demo" in steps.covers("demo", hardcover=False)
    steps.covers("demo", hardcover=True)
    assert covers.calls == [("demo", True, None), ("demo", True, Path("output/demo-hardcover.pdf"))]
    assert "built output/demo.epub" in steps.epub("demo")
    assert builder.calls == [("pdf", "demo"), ("hardcover", "demo")]


def test_failed_verification_raises_with_every_problem(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    layout = project(tmp_path)
    steps, _, _ = real_steps(layout)
    monkeypatch.setattr(PdfVerifier, "verify", lambda self, pdf, config, log=None: ["a", "b"])
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL a\n\[demo\] FAIL b"):
        steps.pdf("demo")
    monkeypatch.setattr(EpubVerifier, "verify", lambda self, path, book: ["epub bad"])
    with pytest.raises(BookBuildError, match=r"\[demo\] FAIL epub bad"):
        steps.epub("demo")


def test_when_the_interior_is_never_built_the_report_has_no_pdf_facts(tmp_path: Path) -> None:
    layout = project(tmp_path)
    result, ok = pipeline(layout, FakeSteps(layout, fail="pdf")).publish("demo")
    assert not ok and [s["name"] for s in result["steps"]] == ["pdf"]
    assert "pdf" not in result and "hardcover_pdf" not in result and result["visual_qa"] is None
    assert result["release_readiness"]["pricing"].get("page_count") is None
    assert "missing artifact: output/demo.pdf" in result["problems"]
