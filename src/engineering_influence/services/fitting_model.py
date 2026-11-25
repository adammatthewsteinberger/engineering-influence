# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A view of a model whose token count is a fitting estimate, for deciding what fits in a prompt."""

from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.provider_descriptor import ProviderDescriptor


class FittingModel(ModelInterface):
    """Everything is the wrapped model's, except the token count, which is an estimate of its own.

    The wrapped model's ``count_tokens`` is an upper bound (UTF-8 bytes for a local model), right for
    reserving spend but far too large for fitting a prompt into a window: a 30-chapter outline is about
    36 KB of text but only about 9,000 tokens. Fitting uses three characters to a token, which is
    generous for English prose (about four characters a token), so a fitted prompt still fits the window.
    The reservation made by ``CallModel`` keeps the wrapped model's count.
    """

    CHARACTERS_PER_TOKEN = 3

    def __init__(self, model: ModelInterface) -> None:
        self._model = model

    def describe(self) -> ProviderDescriptor:
        return self._model.describe()

    def availability(self) -> ModelAvailability:
        return self._model.availability()

    def count_tokens(self, request: ModelRequest) -> int:
        characters = len(request.system) + len(request.prompt)
        return -(-characters // self.CHARACTERS_PER_TOKEN)

    def complete(self, request: ModelRequest) -> ModelResponse:
        return self._model.complete(request)
