# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The free, open-source model a run uses when nothing else is chosen."""

from collections.abc import Mapping
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.interfaces.local_default_model_interface import (
    LocalDefaultModelInterface,
)


class LocalDefaultModel(LocalDefaultModelInterface):
    """``gpt-oss:20b`` (Apache 2.0) served by Ollama on this machine, which costs nothing per token.

    It was chosen by running the installed candidates on the author's 24 GB Apple Silicon laptop over three
    book-copy tasks: it was the only one to keep to a no-dashes, no-filler instruction every time, and it fits in
    about 13 GB. It is a default, not a promise: ``EI_LOCAL_MODEL`` and ``EI_LOCAL_URL`` name another model or server
    that speaks the OpenAI chat shape (Ollama, llama.cpp, vLLM, LM Studio).

    The model reasons before it answers and the reasoning counts against a stage's token cap, so the profile asks
    for ``low`` reasoning effort. The context window is stated as ``CONTEXT_WINDOW`` and the server must really
    offer it: Ollama's own default is smaller, so start it with ``OLLAMA_CONTEXT_LENGTH=32768`` or more.
    A prompt is assembled to fit the stated window, so a server that quietly offers less would cut a prompt short.
    """

    MODEL: ClassVar[str] = "gpt-oss:20b"
    URL: ClassVar[str] = "http://127.0.0.1:11434"
    CONTEXT_WINDOW: ClassVar[int] = 32_768
    MAX_OUTPUT_TOKENS: ClassVar[int] = 8_192
    LICENCE_URL: ClassVar[str] = "https://huggingface.co/openai/gpt-oss-20b"
    PRICES_EFFECTIVE: ClassVar[str] = "2026-01-01"
    NAME: ClassVar[str] = "local-default"

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._model = environment.get("EI_LOCAL_MODEL", "").strip() or self.MODEL
        self._url = environment.get("EI_LOCAL_URL", "").strip() or self.URL

    def profile(self) -> ModelProfile:
        """How to reach it: an OpenAI-compatible server on this machine, no key."""
        try:
            return ModelProfile(
                name=self.NAME,
                adapter="openai_compatible",
                provider="local",
                model=self._model,
                base_url=self._url,
                reasoning_effort="low",
            )
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_LOCAL_MODEL_INVALID",
                message=f"EI_LOCAL_MODEL or EI_LOCAL_URL is not usable: {error}",
                http_status=503,
            ) from error

    def descriptor(self) -> ProviderDescriptor:
        """Its limits and its price, which is nothing."""
        return ProviderDescriptor(
            provider="local",
            model=self._model,
            family="local",
            context_window=self.CONTEXT_WINDOW,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            input_micro_usd_per_mtok=0,
            output_micro_usd_per_mtok=0,
            cache_read_micro_usd_per_mtok=0,
            cache_write_micro_usd_per_mtok=0,
            batch_discount_percent=0,
            price_effective=self.PRICES_EFFECTIVE,
            usage_policy_url=self.LICENCE_URL,
        )
