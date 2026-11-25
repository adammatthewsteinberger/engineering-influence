# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outbound URL pinner port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.pin_decision import PinDecision


class OutboundUrlPinnerInterface(ABC):
    """Decide where a caller-supplied URL may be fetched, and fix the address it is fetched from."""

    __slots__ = ()

    @abstractmethod
    def pin(self, url: str) -> PinDecision:
        """The address to connect to, checked once, or the reason the URL may not be used.

        The caller connects to the address it is given and to no other, so a name that resolves
        differently a moment later cannot send the request somewhere the check did not see.
        """
