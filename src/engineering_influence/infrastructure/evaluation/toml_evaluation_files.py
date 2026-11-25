# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the rubric, the set and the baseline of an evaluation."""

import json
import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.evaluation_files_interface import EvaluationFilesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.rubric import Rubric
from engineering_influence.models.rubric_dimension import RubricDimension


class TomlEvaluationFiles(EvaluationFilesInterface):
    """Strict readers: an unknown key, a value of the wrong kind or a file that cannot be read is refused with its name.

    The rubric and the set are TOML a person reviews; the baseline is the JSON report of an earlier evaluation (only its
    ``dimension_means`` is read). Nothing here is run, fetched or sent to a model apart from what the judge is shown.
    """

    MAX_BYTES = 256 * 1024

    def rubric(self, path: Path) -> Rubric:
        """The rubric in the TOML file, or an ApplicationError (EVALUATION_FILE_INVALID) that says what is wrong."""
        data = self._toml(path, {"version", "pass_mean", "max_drop", "dimension"})
        dimensions = []
        for item in self._list(path, data, "dimension"):
            table = self._table(path, item, {"name", "question", "kinds", "anchors"})
            anchors = self._table(path, table.get("anchors"), {"1", "3", "5"})
            try:
                dimensions.append(
                    RubricDimension(
                        name=table.get("name", ""),
                        question=table.get("question", ""),
                        anchors=tuple(
                            (int(score), text) for score, text in sorted(anchors.items())
                        ),
                        kinds=tuple(table.get("kinds", ())),
                    )
                )
            except (TypeError, ValueError) as error:
                raise self._invalid(path, str(error)) from error
        try:
            return Rubric(
                version=data.get("version"),  # type: ignore[arg-type]
                pass_mean=float(data.get("pass_mean", 0)),
                max_drop=float(data.get("max_drop", -1)),
                dimensions=tuple(dimensions),
            )
        except (TypeError, ValueError) as error:
            raise self._invalid(path, str(error)) from error

    def cases(self, path: Path) -> tuple[EvaluationCase, ...]:
        """The set of books in the TOML file, in its order."""
        data = self._toml(path, {"case"})
        cases = []
        for item in self._list(path, data, "case"):
            table = self._table(
                path, item, {"name", "kind", "idea", "title_hint", "target_words", "trim_size"}
            )
            try:
                cases.append(
                    EvaluationCase(
                        name=table.get("name", ""),
                        kind=BookKind(table.get("kind", "")),
                        idea=table.get("idea", ""),
                        title_hint=table.get("title_hint"),
                        target_words=table.get("target_words"),
                        trim_size=table.get("trim_size"),
                    )
                )
            except (TypeError, ValueError, AttributeError) as error:
                raise self._invalid(path, f"{table.get('name', 'a case')}: {error}") from error
        names = [case.name for case in cases]
        if len(set(names)) != len(names):
            raise self._invalid(path, "each case is named once")
        return tuple(cases)

    def baseline(self, path: Path) -> dict[str, float]:
        """The dimension means of an earlier evaluation report."""
        text = self._read(path)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise self._invalid(path, f"it is not valid JSON ({error.msg})") from error
        means = data.get("dimension_means") if isinstance(data, dict) else None
        if not isinstance(means, dict) or not means:
            raise self._invalid(path, "it has no dimension_means; is it an evaluation report?")
        if any(not isinstance(v, int | float) or isinstance(v, bool) for v in means.values()):
            raise self._invalid(path, "every dimension mean is a number")
        return {str(name): float(value) for name, value in means.items()}

    def _read(self, path: Path) -> str:
        try:
            if path.stat().st_size > self.MAX_BYTES:
                raise self._invalid(path, f"it is larger than {self.MAX_BYTES} bytes")
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise self._invalid(path, f"it cannot be read ({type(error).__name__})") from error

    def _toml(self, path: Path, keys: set[str]) -> dict[str, Any]:
        try:
            data = tomllib.loads(self._read(path))
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(path, f"it is not valid TOML: {error}") from error
        return self._table(path, data, keys)

    def _table(self, path: Path, value: Any, keys: set[str]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self._invalid(path, "a table was expected")
        unknown = sorted(set(value) - keys)
        if unknown:
            raise self._invalid(path, f"unknown keys {unknown}")
        return value

    def _list(self, path: Path, data: dict[str, Any], key: str) -> list[Any]:
        found = data.get(key)
        if not isinstance(found, list) or not found:
            raise self._invalid(path, f"it needs at least one [[{key}]]")
        return found

    @staticmethod
    def _invalid(path: Path, why: str) -> ApplicationError:
        return ApplicationError(
            code="EVALUATION_FILE_INVALID",
            message=f"{path} cannot be used: {why}",
            http_status=422,
        )
