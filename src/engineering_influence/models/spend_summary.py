# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a run spent against what was expected, for the quality report."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.spend_summary_interface import SpendSummaryInterface


@dataclass(frozen=True, slots=True)
class SpendSummary(SpendSummaryInterface):
    """The cap, what was spent and the estimate made from the brief alone, all in micro-dollars.

    Recording the estimate beside the real figure on every finished run is how the estimator's constants are calibrated;
    it says nothing by itself about whether the estimate was good.
    """

    cap: int
    spent: int
    estimated: int | None = None
    estimated_high: int | None = None

    def __post_init__(self) -> None:
        amounts: tuple[tuple[str, int | None], ...] = (
            ("cap", self.cap),
            ("spent", self.spent),
            ("estimated", self.estimated),
            ("estimated_high", self.estimated_high),
        )
        for label, value in amounts:
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{label} is a whole number of micro-dollars, not less than none")

    def ratio(self) -> float | None:
        """Spent divided by the expected cost, to three places, or None when there was no estimate."""
        if not self.estimated:
            return None
        return round(self.spent / self.estimated, 3)
