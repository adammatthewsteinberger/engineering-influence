"""The codes a client can be told, frozen: a script that handles ``RUN_NOT_FOUND`` or ``stage-failed`` keeps working."""

import ast
import re
from pathlib import Path

from snapshot import Snapshot

import engineering_influence

ROOT = Path(engineering_influence.__file__).parent
ERROR = re.compile(r"[A-Z][A-Z0-9_]*")
ISSUE = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")


class Codes:
    """Every literal code the application can raise, by reading its source.

    An **error code** is what a request or command is refused with (``code="RUN_NOT_FOUND"`` in any call, or
    ``ApplicationError("...")``). An **issue code** is what a run records about its book (``QualityIssue(stage, "code",
    ...)`` or ``QualityIssue(..., code="...")``) and what the run summary and ``quality-report.json`` carry. A code
    built at run time (a continuity finding's kind) is not a literal and is not listed.
    """

    @classmethod
    def found(cls) -> tuple[list[str], list[str]]:
        errors: set[str] = set()
        issues: set[str] = set()
        for path in sorted(ROOT.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = cls._assigned(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    (issues if cls._name(node) == "QualityIssue" else errors).update(
                        cls._codes(node, names)
                    )
        return sorted(errors), sorted(issues)

    @classmethod
    def _assigned(cls, tree: ast.AST) -> dict[str, set[str]]:
        """Names given a literal or a conditional of literals, so ``code = "a" if x else "b"`` is read as both."""
        found: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                options = cls._literals(node.value)
                if options:
                    found.setdefault(node.targets[0].id, set()).update(options)
        return found

    @classmethod
    def _literals(cls, node: ast.AST) -> set[str]:
        text = cls._text(node)
        if text is not None:
            return {text}
        if isinstance(node, ast.IfExp):
            return cls._literals(node.body) | cls._literals(node.orelse)
        return set()

    @staticmethod
    def _text(node: ast.AST) -> str | None:
        return (
            node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None
        )

    @staticmethod
    def _name(call: ast.Call) -> str:
        return call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, "attr", "")

    @classmethod
    def _codes(cls, call: ast.Call, names: dict[str, set[str]]) -> list[str]:
        name = cls._name(call)
        values = [keyword.value for keyword in call.keywords if keyword.arg == "code"]
        if name == "ApplicationError" and call.args:
            values.append(call.args[0])
        if name == "QualityIssue" and len(call.args) > 1:
            values.append(call.args[1])
        found: set[str] = set()
        for value in values:
            found |= cls._literals(value)
            if isinstance(value, ast.Name):
                found |= names.get(value.id, set())
        return sorted(found)


def test_the_error_codes_are_frozen() -> None:
    Snapshot("error_codes").check(Codes.found()[0])


def test_the_issue_codes_a_run_records_are_frozen() -> None:
    Snapshot("issue_codes").check(Codes.found()[1])


def test_error_codes_are_upper_snake_case_and_an_issue_code_is_that_or_lower_kebab_case() -> None:
    errors, issues = Codes.found()
    assert errors and issues
    assert all(ERROR.fullmatch(code) for code in errors)
    assert all(ERROR.fullmatch(code) or ISSUE.fullmatch(code) for code in issues)
