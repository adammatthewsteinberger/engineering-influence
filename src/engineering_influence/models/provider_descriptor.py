# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Everything the run must know about one model before calling it."""

from dataclasses import dataclass
from datetime import date

from engineering_influence.models.book_brief import BookBrief
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
    falls short. ``price_effective`` is the ISO date the prices take effect, because they change.

    A call whose prompt exceeds ``long_context_threshold_tokens`` (zero means there is no such
    tier) is billed at ``long_context_input_percent`` of every input rate and
    ``long_context_output_percent`` of the output rate. Neither percentage can be below 100.

    ``max_violence`` and ``max_heat`` are the most a novel may ask of this model: levels the person recorded after
    reading ``usage_policy_url``, not something this project asserts about any provider. Unset means not recorded.
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
    long_context_threshold_tokens: int = 0
    long_context_input_percent: int = 100
    long_context_output_percent: int = 100
    max_violence: str | None = None
    max_heat: str | None = None

    def __post_init__(self) -> None:
        """Validate the model's identity, limits and prices when it is built."""
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
        try:
            date.fromisoformat(self.price_effective)
        except ValueError as error:
            raise ValueError("price_effective must be an ISO date such as 2026-11-01") from error
        for label, ceiling, levels in (
            ("max_violence", self.max_violence, BookBrief.VIOLENCE_LEVELS),
            ("max_heat", self.max_heat, BookBrief.HEAT_LEVELS),
        ):
            if ceiling is not None and ceiling not in levels:
                raise ValueError(f"{label} must be one of {', '.join(levels)}")
        if self.long_context_threshold_tokens < 0:
            raise ValueError("the long-context threshold cannot be negative")
        if min(self.long_context_input_percent, self.long_context_output_percent) < 100:
            raise ValueError("a long-context tier cannot be cheaper than the standard rate")
        if self.long_context_threshold_tokens == 0 and (
            self.long_context_input_percent != 100 or self.long_context_output_percent != 100
        ):
            raise ValueError("long-context percentages need a long-context threshold")

    @staticmethod
    def _ceil_div(amount: int, divisor: int) -> int:
        return -(-amount // divisor)

    def _is_long_context(self, prompt_tokens: int) -> bool:
        return 0 < self.long_context_threshold_tokens < prompt_tokens

    def cost_micro_usd(self, usage: ModelUsage, batch: bool = False) -> int:
        """What a finished call cost, rounded up to a whole micro-dollar."""
        prompt_tokens = usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens
        long = self._is_long_context(prompt_tokens)
        input_percent = self.long_context_input_percent if long else 100
        output_percent = self.long_context_output_percent if long else 100
        input_part = (
            usage.input_tokens * self.input_micro_usd_per_mtok
            + usage.cache_read_tokens * self.cache_read_micro_usd_per_mtok
            + usage.cache_write_tokens * self.cache_write_micro_usd_per_mtok
        )
        output_part = usage.output_tokens * self.output_micro_usd_per_mtok
        weighted = input_part * input_percent + output_part * output_percent
        if batch:
            return self._ceil_div(
                weighted * (100 - self.batch_discount_percent), MILLION * 100 * 100
            )
        return self._ceil_div(weighted, MILLION * 100)

    def worst_case_micro_usd(self, input_tokens: int, max_output_tokens: int) -> int:
        """The most a call can cost, to reserve before sending it.

        Input is priced at the dearer of the plain and cache-write rates, the output at its cap,
        and the long-context tier is applied whenever the prompt could reach it, so the actual
        cost can only come in under the reservation.
        """
        if input_tokens < 0 or max_output_tokens < 0:
            raise ValueError("token counts cannot be negative")
        long = self._is_long_context(input_tokens)
        input_percent = self.long_context_input_percent if long else 100
        output_percent = self.long_context_output_percent if long else 100
        input_rate = max(self.input_micro_usd_per_mtok, self.cache_write_micro_usd_per_mtok)
        weighted = (
            input_tokens * input_rate * input_percent
            + max_output_tokens * self.output_micro_usd_per_mtok * output_percent
        )
        return self._ceil_div(weighted, MILLION * 100)
