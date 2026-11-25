# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""FittingModel: the wrapped model for everything, and a character estimate for counting tokens."""

import pytest

from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.services.fitting_model import FittingModel


class Wrapped(ModelInterface):
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def describe(self) -> object:
        return "described"

    def availability(self) -> object:
        return "available"

    def count_tokens(self, request: ModelRequest) -> int:
        return 999_999

    def complete(self, request: ModelRequest) -> object:
        self.requests.append(request)
        return "completed"


def request(system: str, prompt: str) -> ModelRequest:
    return ModelRequest(system=system, prompt=prompt, max_output_tokens=10, prompt_version="v@1")


def test_everything_but_the_count_is_the_wrapped_models() -> None:
    wrapped = Wrapped()
    model = FittingModel(wrapped)
    assert model.describe() == "described"
    assert model.availability() == "available"
    assert model.complete(request("s", "p")) == "completed"
    assert wrapped.requests == [request("s", "p")]


@pytest.mark.parametrize(
    ("system", "prompt", "tokens"),
    [
        ("", "a", 1),
        ("abc", "d", 2),
        ("ab", "cd", 2),
        ("a" * 300, "b" * 300, 200),
        ("é" * 6, "x", 3),
    ],
)
def test_a_token_is_three_characters_rounded_up(system: str, prompt: str, tokens: int) -> None:
    assert FittingModel(Wrapped()).count_tokens(request(system, prompt)) == tokens


def test_the_wrapped_models_count_is_untouched_for_spend() -> None:
    assert Wrapped().count_tokens(request("a", "b")) == 999_999
