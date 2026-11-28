# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks that the free local model is ready: the server, the model, an answer and the context."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.ollama_server_interface import OllamaServerInterface
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.services.interfaces.local_default_model_interface import (
    LocalDefaultModelInterface,
)
from engineering_influence.services.interfaces.local_model_doctor_interface import (
    LocalModelDoctorInterface,
)


class LocalModelDoctor(LocalModelDoctorInterface):
    """Four checks, in the order a person would fix them, each stopping the rest when it fails.

    1. **server**: something answers at the address. Ollama is recognised by ``/api/tags``; another server that
       speaks the chat shape passes with a note, and the next two checks are skipped.
    2. **model**: the model is pulled (Ollama only). The fix named is ``ollama pull``.
    3. **answers**: one tiny real completion, which costs nothing. An empty reply is a failure, because a model
       that reasons can spend a whole cap before it writes a word.
    4. **context**: the context length Ollama loaded the model with is at least the window a prompt is assembled to
       fit. Ollama's own default is smaller, and it would cut a prompt short without saying so.

    The model's reply is not printed, only how many tokens it took, and the server's replies are only compared.
    """

    PROMPT = "Reply with the single word: ready."
    MAX_OUTPUT_TOKENS = 256
    NAME = "local"

    def __init__(
        self,
        free: LocalDefaultModelInterface,
        model: ModelInterface,
        server: OllamaServerInterface,
    ) -> None:
        """Remember the free model, the model, and the server the checks look at."""
        self._free = free
        self._model = model
        self._server = server

    def check(self) -> tuple[DoctorFinding, ...]:
        """One finding for each check that could be made, stopping at the first thing that makes the rest pointless."""
        profile = self._free.profile()
        name, url = profile.model, profile.base_url
        try:
            pulled = self._server.models()
        except ApplicationError:
            return (
                self._finding(
                    "server",
                    False,
                    f"nothing answers at {url}; install Ollama from https://ollama.com and start it, "
                    "or set EI_LOCAL_URL to the server you run",
                ),
            )
        found = [
            self._finding(
                "server",
                True,
                f"Ollama answers at {url}"
                if pulled is not None
                else f"something answers at {url}, but it is not Ollama, so the model and context checks are skipped",
            )
        ]
        if pulled is not None and name not in pulled and f"{name}:latest" not in pulled:
            found.append(
                self._finding("model", False, f"{name} is not pulled; run: ollama pull {name}")
            )
            return tuple(found)
        if pulled is not None:
            found.append(self._finding("model", True, f"{name} is pulled"))
        try:
            reply = self._model.complete(
                ModelRequest(
                    system="",
                    prompt=self.PROMPT,
                    max_output_tokens=self.MAX_OUTPUT_TOKENS,
                    prompt_version="doctor-local@1",
                )
            )
        except (TransientStageError, CapacityExhaustedError, ApplicationError) as error:
            found.append(
                self._finding("answers", False, f"could not complete: {self._flat(str(error))}")
            )
            return tuple(found)
        if not reply.text.strip():
            found.append(
                self._finding(
                    "answers",
                    False,
                    f"{name} returned nothing (it stopped for {reply.stop_reason}); "
                    "its reasoning may have used the whole cap",
                )
            )
            return tuple(found)
        found.append(
            self._finding("answers", True, f"{name} replied in {reply.usage.output_tokens} tokens")
        )
        if pulled is not None:
            found.append(self._context(name))
        return tuple(found)

    def _context(self, name: str) -> DoctorFinding:
        wanted = self._free.descriptor().context_window
        loaded = self._server.loaded_context(name)
        if loaded is None:
            return self._finding(
                "context",
                False,
                f"Ollama did not say what context {name} was loaded with, so it cannot be checked",
            )
        if loaded < wanted:
            return self._finding(
                "context",
                False,
                f"Ollama loaded {name} with a context of {loaded}, below the {wanted} a prompt is assembled to "
                f"fit, and it would cut a prompt short; start Ollama with OLLAMA_CONTEXT_LENGTH={wanted}",
            )
        return self._finding(
            "context", True, f"{loaded} tokens, at least the {wanted} a prompt is assembled to fit"
        )

    def _finding(self, check: str, passed: bool, detail: str) -> DoctorFinding:
        return DoctorFinding(self.NAME, check, passed, detail)

    @staticmethod
    def _flat(text: str) -> str:
        return " ".join("".join(c if c.isprintable() else " " for c in text).split())[:200]
