"""Non-loosenable methodology constraints."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LimitsOnMeans:
    """Fixed constraints that apply to every project and autonomy mode."""

    require_source_for_factual_claims: bool = True
    prohibit_fabricated_evidence: bool = True
    require_bounded_spend: bool = True
    require_recoverable_side_effects: bool = True
