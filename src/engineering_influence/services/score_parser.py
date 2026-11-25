# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the judge's answer."""

import json
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.rubric import Rubric
from engineering_influence.services.interfaces.score_parser_interface import ScoreParserInterface


class ScoreParser(ScoreParserInterface):
    """The first JSON object in the answer, so a preamble or a code fence around it does no harm.

    It must have a ``scores`` object with exactly the rubric's dimensions, each a whole number in the scale (a boolean or
    a float such as 4.5 is refused: a half point is not on the scale) and a reason. Anything else is refused with a message
    that says what is wrong, because a missing or invented score would quietly move a mean.
    """

    def parse(self, text: str, dimensions: tuple[str, ...]) -> tuple[tuple[str, int, str], ...]:
        """The (dimension, score, reason) of each dimension, in the order given; an ApplicationError if the answer is unusable."""
        data = self._object(text)
        scores = data.get("scores")
        if not isinstance(scores, dict):
            raise self._invalid("it has no ``scores`` object")
        missing = [name for name in dimensions if name not in scores]
        extra = sorted(set(scores) - set(dimensions))
        if missing or extra:
            raise self._invalid(
                f"it must score exactly {list(dimensions)}; missing {missing}, unknown {extra}"
            )
        found = []
        for name in dimensions:
            entry = scores[name]
            if not isinstance(entry, dict):
                raise self._invalid(f"{name} is not an object with a score and a reason")
            score, reason = entry.get("score"), entry.get("reason")
            if type(score) is not int or not Rubric.LOW <= score <= Rubric.HIGH:
                raise self._invalid(
                    f"{name}: the score is a whole number from {Rubric.LOW} to {Rubric.HIGH}, not {score!r}"
                )
            if not isinstance(reason, str) or not reason.strip():
                raise self._invalid(f"{name}: a score comes with its reason")
            found.append((name, score, " ".join(reason.split())))
        return tuple(found)

    def _object(self, text: str) -> dict[str, Any]:
        start = text.find("{")
        if start < 0:
            raise self._invalid("it holds no JSON object")
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError as error:
            raise self._invalid(f"it is not valid JSON ({error.msg})") from error
        return dict(value)  # decoding from a ``{`` can only give an object

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="JUDGE_ANSWER_INVALID",
            message=f"the judge's answer cannot be used: {why}",
            http_status=502,
        )
