# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JSON form of a book run, as stored by the SQL repository."""

import json
from dataclasses import asdict
from typing import Any

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_input import RunInput
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.interfaces.book_run_codec_interface import (
    BookRunCodecInterface,
)


class BookRunCodec(BookRunCodecInterface):
    """Encodes through ``asdict`` and rebuilds each model, so the models re-check their own rules."""

    def encode(self, run: BookRun) -> str:
        return json.dumps(asdict(run), sort_keys=True)

    def decode(self, text: str) -> BookRun:
        document: dict[str, Any] = json.loads(text)
        brief = document["brief"]
        plan = document["plan"]
        return BookRun(
            run_id=document["run_id"],
            brief=BookBrief(
                **{
                    **brief,
                    "kind": BookKind(brief["kind"]),
                    "inputs": tuple(RunInput(**item) for item in brief.get("inputs", ())),
                }
            ),
            plan=StagePlan(kind=BookKind(plan["kind"]), stages=tuple(plan["stages"])),
            budget=Budget(**document["budget"]),
            stage=document["stage"],
            status=RunStatus(document["status"]),
            issues=tuple(QualityIssue(**issue) for issue in document["issues"]),
        )
