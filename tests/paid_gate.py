# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A test marked ``paid`` spends real money, so it runs only when the environment allows it."""

from collections.abc import Mapping

import pytest


class PaidGate:
    """Fails a ``paid`` test before it starts unless ``EI_ALLOW_PAID`` is exactly ``1``.

    The marker already keeps these tests out of the default run. This is the second lock: a person
    who types ``pytest -m paid`` still has to say, in the environment, that they mean to spend.
    A failure rather than a skip, so a scheduled run with the variable missing goes red instead
    of passing without having tested anything.
    """

    VARIABLE = "EI_ALLOW_PAID"

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._environment = environment

    def pytest_runtest_setup(self, item: pytest.Item) -> None:
        """Refuse to start a paid test the environment has not allowed."""
        if item.get_closest_marker("paid") is None:
            return
        if self._environment.get(self.VARIABLE) != "1":
            pytest.fail(
                f"{item.nodeid} is marked paid and would spend money: "
                f"set {self.VARIABLE}=1 to allow it",
                pytrace=False,
            )
