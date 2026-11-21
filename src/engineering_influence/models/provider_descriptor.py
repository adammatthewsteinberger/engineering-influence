# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Everything the run must know about one model before calling it."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.provider_descriptor_interface import (
    ProviderDescriptorInterface,
)
from engineering_influence.models.model_usage import ModelUsage

MILLION = 1_000_000


@dataclass(frozen=True, slots=True)
class ProviderDescriptor(ProviderDescriptorInterface):
    """One model's identity, limits, prices and usage policy.

    Prices are whole micro-dollars per million tokens, so cost arithmetic stays in integers
    and always rounds up: a run is never charged less than it owes, and a reservation never
    falls short. ``price_effective`` is the ISO date the prices were read, because they change.
    """

    provider: str
    model: str
    family: str
    context_window: int
    max_output_tokens: int
    input_micro_usd_per_mtok: int
    output_micro_usd_per_mtok: int
    cache_read_micro_usd_per_mtok: int
    cache_write_micro_usd_per_mtok: int
    batch_discount_percent: int
    price_effective: str
    usage_policy_url: str

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip() or not self.family.strip():
            raise ValueError("a descriptor needs a provider, a model and a family")
        if self.context_window <= 0 or self.max_output_tokens <= 0:
            raise ValueError("a descriptor needs positive limits")
        prices = (
            self.input_micro_usd_per_mtok,
            self.output_micro_usd_per_mtok,
            self.cache_read_micro_usd_per_mtok,
            self.cache_write_micro_usd_per_mtok,
        )
        if min(prices) < 0:
            raise ValueError("prices cannot be negative")
        if not 0 <= self.batch_discount_percent <= 100:
            raise ValueError("a batch discount is a percentage from 0 to 100")

    @staticmethod
    def _ceil_div(amount: int, divisor: int) -> int:
        return -(-amount // divisor)

    def cost_micro_usd(self, usage: ModelUsage, batch: bool = False) -> int:
        """What a finished call cost, rounded up to a whole micro-dollar."""
        weighted = (
            usage.input_tokens * self.input_micro_usd_per_mtok
            + usage.output_tokens * self.output_micro_usd_per_mtok
            + usage.cache_read_tokens * self.cache_read_micro_usd_per_mtok
            + usage.cache_write_tokens * self.cache_write_micro_usd_per_mtok
        )
        if batch:
            weighted = weighted * (100 - self.batch_discount_percent)
            return self._ceil_div(weighted, MILLION * 100)
        return self._ceil_div(weighted, MILLION)

    def worst_case_micro_usd(self, input_tokens: int, max_output_tokens: int) -> int:
        """The most a call can cost, to reserve before sending it.

        Input is priced at the dearer of the plain and cache-write rates, and the output at
        its cap, so the actual cost can only come in under the reservation.
        """
        if input_tokens < 0 or max_output_tokens < 0:
            raise ValueError("token counts cannot be negative")
        input_rate = max(self.input_micro_usd_per_mtok, self.cache_write_micro_usd_per_mtok)
        weighted = input_tokens * input_rate + max_output_tokens * self.output_micro_usd_per_mtok
        return self._ceil_div(weighted, MILLION)
