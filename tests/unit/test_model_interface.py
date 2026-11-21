"""The model port can be implemented by a fake, which is how every later test supplies a model."""

import pytest

from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor

DESCRIPTOR = ProviderDescriptor(
    provider="fake",
    model="fake-1",
    family="fake",
    context_window=1000,
    max_output_tokens=100,
    input_micro_usd_per_mtok=1_000_000,
    output_micro_usd_per_mtok=2_000_000,
    cache_read_micro_usd_per_mtok=100_000,
    cache_write_micro_usd_per_mtok=1_250_000,
    batch_discount_percent=50,
    price_effective="2026-11-01",
    usage_policy_url="https://example.test/policy",
)


class FakeModel(ModelInterface):
    """Answers with the prompt reversed, or reports exhausted credit."""

    def __init__(self, availability: ModelAvailability = ModelAvailability.AVAILABLE) -> None:
        self._availability = availability

    def describe(self) -> ProviderDescriptor:
        return DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return self._availability

    def count_tokens(self, request: ModelRequest) -> int:
        return len(request.prompt.split())

    def complete(self, request: ModelRequest) -> ModelResponse:
        if self._availability is not ModelAvailability.AVAILABLE:
            raise CapacityExhaustedError(self._availability.value)
        usage = ModelUsage(self.count_tokens(request), 1)
        return ModelResponse(request.prompt[::-1], usage, "fake-1-2026", "end_turn")


REQUEST = ModelRequest(
    system="s", prompt="one two three", max_output_tokens=50, prompt_version="v1"
)


def test_a_fake_satisfies_the_port_and_the_reservation_covers_the_call() -> None:
    model = FakeModel()
    reserved = model.describe().worst_case_micro_usd(
        model.count_tokens(REQUEST), REQUEST.max_output_tokens
    )
    response = model.complete(REQUEST)
    assert response.text == "eerht owt eno"
    assert model.describe().cost_micro_usd(response.usage) <= reserved


def test_a_blocked_model_raises_the_capacity_error_the_run_parks_on() -> None:
    model = FakeModel(ModelAvailability.CREDITS_EXHAUSTED)
    assert model.availability() is ModelAvailability.CREDITS_EXHAUSTED
    with pytest.raises(CapacityExhaustedError, match="credits_exhausted"):
        model.complete(REQUEST)
