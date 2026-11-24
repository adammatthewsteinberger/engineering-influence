# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes evaluation.json."""

import json

from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.models.evaluation_verdict import EvaluationVerdict
from engineering_influence.models.rubric import Rubric
from engineering_influence.services.interfaces.evaluation_reporter_interface import (
    EvaluationReporterInterface,
)


class EvaluationReporter(EvaluationReporterInterface):
    """The same inputs give the same bytes, and the document is its own baseline.

    ``dimension_means`` is what the next release is compared against: committing this file as the baseline is how a
    release becomes the thing the next one is measured by.
    """

    def render(self, report: EvaluationReport, verdict: EvaluationVerdict, rubric: Rubric) -> bytes:
        """The evaluation report, as bytes."""
        spent, expected = report.spent(), report.estimated()
        document = {
            "schema_version": 1,
            "release": report.release,
            "rubric_version": rubric.version,
            "pass_mean": rubric.pass_mean,
            "max_drop": rubric.max_drop,
            "dimension_means": report.means(),
            "spend": {
                "making_micro_usd": spent,
                "estimated_micro_usd": expected,
                "estimate_error_percent": (
                    None
                    if not expected or not spent
                    else round(abs(expected - spent) * 100 / spent, 1)
                ),
                "judging_micro_usd": report.judged(),
            },
            "verdict": {"passed": verdict.passed(), "failures": list(verdict.failures)},
            "cases": [
                {
                    "case": book.case,
                    "kind": book.kind.value,
                    "run_status": book.run_status,
                    "finished": book.finished,
                    "title": book.title,
                    "chapters": len(book.chapters),
                    "words": sum(len(chapter.split()) for chapter in book.chapters),
                    "spent_micro_usd": book.spent_micro_usd,
                    "estimated_micro_usd": book.estimated_micro_usd,
                    "issues": list(book.issues),
                    "scores": (
                        []
                        if score is None
                        else [
                            {"dimension": name, "score": value, "reason": reason}
                            for name, value, reason in score.scores
                        ]
                    ),
                }
                for book, score in report.results
            ],
        }
        return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
