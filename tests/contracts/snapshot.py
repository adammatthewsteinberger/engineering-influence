"""Compare a public contract with the copy committed in ``snapshots/``, and say what to do when they differ.

A contract is frozen when a test fails the moment it changes. Changing one on purpose is allowed (see
``docs/COMPATIBILITY.md``): rerun the contract tests with ``EI_UPDATE_CONTRACTS=1``, read the diff of the snapshot,
say in the changelog whether the change is compatible, and commit both.
"""

import json
import os
from pathlib import Path
from typing import Any

SNAPSHOTS = Path(__file__).parent / "snapshots"
UPDATE = "EI_UPDATE_CONTRACTS"


class Snapshot:
    """One committed JSON document, compared by value so key order and whitespace never matter."""

    def __init__(self, name: str) -> None:
        self.path = SNAPSHOTS / f"{name}.json"

    PROSE = ("description", "summary", "operationId")

    @staticmethod
    def schema(document: Any) -> Any:
        """A JSON Schema or OpenAPI document without its prose and its generated names.

        A docstring (``description``), a title made from a function name (``summary``) and the id made from a handler's
        name (``operationId``) are documentation, so rewording or renaming one is not a contract change. Only a
        string-valued key is dropped: a property that is *called* ``description`` has a schema (an object) for its value
        and stays.
        """
        if isinstance(document, dict):
            return {
                key: Snapshot.schema(value)
                for key, value in document.items()
                if not (key in Snapshot.PROSE and isinstance(value, str))
            }
        if isinstance(document, list):
            return [Snapshot.schema(item) for item in document]
        return document

    @staticmethod
    def render(document: Any) -> str:
        """The document as the text that is committed: sorted keys, two-space indent, one trailing newline."""
        return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    def check(self, document: Any) -> None:
        """Pass when the document equals the committed one; write it when ``EI_UPDATE_CONTRACTS=1``."""
        text = self.render(document)
        if os.environ.get(UPDATE) == "1":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(text, encoding="utf-8")
            return
        assert self.path.is_file(), (
            f"no snapshot for this contract yet: run `{UPDATE}=1 uv run pytest tests/contracts` and commit {self.path}"
        )
        committed = self.path.read_text(encoding="utf-8")
        assert json.loads(committed) == json.loads(text), (
            f"the public contract in {self.path.name} changed. If that is intended, run "
            f"`{UPDATE}=1 uv run pytest tests/contracts`, read the diff, add a changelog entry that says whether "
            "it is compatible (docs/COMPATIBILITY.md), and commit the new snapshot."
        )
