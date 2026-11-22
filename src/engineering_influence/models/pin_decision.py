# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pinner's answer for one URL: a target to connect to, or the reason there is none."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.pin_decision_interface import PinDecisionInterface
from engineering_influence.models.pinned_target import PinnedTarget


@dataclass(frozen=True, slots=True)
class PinDecision(PinDecisionInterface):
    """Exactly one of ``target`` (go here) and ``reason`` (a short stable code for why not)."""

    target: PinnedTarget | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if (self.target is None) == (not self.reason):
            raise ValueError("a decision is a target to connect to, or a reason for refusing")

    @classmethod
    def pinned(cls, target: PinnedTarget) -> "PinDecision":
        """Go to this address."""
        return cls(target=target)

    @classmethod
    def refused(cls, reason: str) -> "PinDecision":
        """Do not go anywhere, for this stable reason."""
        return cls(reason=reason)
