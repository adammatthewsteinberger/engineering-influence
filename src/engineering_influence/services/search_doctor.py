# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one real search through each configured provider and reports what came back."""

import re
from typing import ClassVar
from urllib.parse import urlsplit

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.services.interfaces.search_doctor_interface import (
    SearchDoctorInterface,
)


class SearchDoctor(SearchDoctorInterface):
    """Each provider is asked on its own, so a SearXNG that is down is not hidden by a Brave key behind it.

    The research stage tries them in this order and falls back, which is right for a run and wrong for a check. A finding
    shows only how many links came back and the **host** of the first one: titles and addresses come from the
    web and are not printed. The query leaves this machine (to the SearXNG instance, which passes it to the engines it
    uses, or to Brave), so it is one fixed, harmless sentence unless the person gives another.
    """

    COUNT = 5
    SHOWN = 200
    HOST: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z0-9.\-]{1,253}|[0-9A-Fa-f:.]{2,45}")

    def __init__(self, providers: tuple[tuple[str, SearchProviderInterface], ...]) -> None:
        """Remember the search providers, each checked on its own."""
        self._providers = providers

    def check(self, query: str) -> tuple[DoctorFinding, ...]:
        """One finding per provider, in the order the research stage tries them."""
        if not self._providers:
            return (
                DoctorFinding(
                    "search",
                    "configured",
                    False,
                    "no web search is set up: set EI_SEARXNG_URL (a SearXNG instance) or BRAVE_SEARCH_API_KEY",
                ),
            )
        return tuple(self._one(name, provider, query) for name, provider in self._providers)

    def _one(self, name: str, provider: SearchProviderInterface, query: str) -> DoctorFinding:
        try:
            hits = provider.search(query, self.COUNT)
        except TransientStageError as error:
            return self._failed(name, f"could not search: {error}")
        except CapacityExhaustedError as error:
            return self._failed(name, f"its quota or key is used up: {error}")
        except ApplicationError as error:
            return self._failed(name, error.message)
        if not hits:
            return self._failed(name, "it answered, but with no links for that query")
        host = self._host(hits[0].url)
        return DoctorFinding(
            name, "search", True, self._line(f"{len(hits)} links, the first from {host}")
        )

    def _failed(self, name: str, why: str) -> DoctorFinding:
        return DoctorFinding(name, "search", False, self._line(why))

    def _host(self, url: str) -> str:
        """The host of a link from the web, only if it is made of what a host is made of; else a placeholder."""
        host = urlsplit(url).hostname or ""
        return host if self.HOST.fullmatch(host) else "a host with unusual characters"

    def _line(self, text: str) -> str:
        """One printable line, cut: what is printed is never what the web or a server said, unfiltered."""
        flat = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        return flat[: self.SHOWN]
