# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a release meets the bar."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.evaluation_verdict_interface import (
    EvaluationVerdictInterface,
)


@dataclass(frozen=True, slots=True)
class EvaluationVerdict(EvaluationVerdictInterface):
    """It passes when there is nothing to say against it; every reason it does not is listed."""

    failures: tuple[str, ...]

    def passed(self) -> bool:
        """True when no reason was found."""
        return not self.failures
