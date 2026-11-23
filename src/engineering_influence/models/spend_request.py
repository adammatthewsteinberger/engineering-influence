# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a run asks for, when its next model call would spend past the cap."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.spend_request_interface import SpendRequestInterface


@dataclass(frozen=True, slots=True)
class SpendRequest(SpendRequestInterface):
    """The micro-dollars the call needs above the cap, and the stage that asked for them."""

    requested_micro_usd: int
    stage: str

    def __post_init__(self) -> None:
        if self.requested_micro_usd <= 0:
            raise ValueError("a spend request needs a positive amount")
        if not self.stage.strip():
            raise ValueError("a spend request names its stage")
