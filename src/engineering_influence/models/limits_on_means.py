# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Non-loosenable methodology constraints."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.limits_on_means_interface import LimitsOnMeansInterface


@dataclass(frozen=True, slots=True)
class LimitsOnMeans(LimitsOnMeansInterface):
    """Fixed constraints that apply to every project and autonomy mode."""

    require_source_for_factual_claims: bool = True
    prohibit_fabricated_evidence: bool = True
    require_bounded_spend: bool = True
    require_recoverable_side_effects: bool = True
