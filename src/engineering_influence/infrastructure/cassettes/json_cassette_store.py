# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps cassettes as one JSON file each, and refuses to keep or load one that holds a secret."""

import json
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.cassette_store_interface import CassetteStoreInterface
from engineering_influence.interfaces.secret_redactor_interface import SecretRedactorInterface
from engineering_influence.models.cassette import Cassette
from engineering_influence.models.cassette_interaction import CassetteInteraction


class JsonCassetteStore(CassetteStoreInterface):
    """``<root>/<name>.json``, written the same way every time so a re-record diffs cleanly.

    The format is strict: an unknown key, a wrong ``format`` or a file whose ``name`` is not its
    file name is refused. Both ``save`` and ``load`` ask the redactor whether the cassette still
    holds a secret and refuse if it does, so a leak is stopped on the way in and again on the way
    out, whatever recorded it.
    """

    FORMAT = 1
    KEYS = frozenset({"format", "name", "provider", "note", "interactions"})
    ENTRY_KEYS = frozenset({"request", "response"})
    REQUEST_KEYS = frozenset({"method", "path", "body"})
    RESPONSE_KEYS = frozenset({"status", "body"})

    def __init__(self, root: Path, redactor: SecretRedactorInterface) -> None:
        """Remember the folder and the redactor used for every cassette."""
        self._root = root
        self._redactor = redactor

    def load(self, name: str) -> Cassette:
        """The named cassette, or an ApplicationError (CASSETTE_INVALID) when it is not usable."""
        if not Cassette.NAME.fullmatch(name):
            raise self._invalid(f"{name!r} is not a cassette name")
        try:
            data = json.loads(self._path(name).read_text(encoding="utf-8"))
        except OSError as error:
            raise self._invalid(f"there is no cassette named {name!r}") from error
        except ValueError as error:
            raise self._invalid(f"cassette {name!r} is not valid JSON: {error}") from error
        if self._redactor.leaks(data):
            raise self._invalid(f"cassette {name!r} holds something that looks like a secret")
        return self._build(name, data)

    def save(self, cassette: Cassette) -> None:
        """Keep the cassette, or raise an ApplicationError (CASSETTE_INVALID) rather than keep a secret."""
        payload = self._payload(cassette)
        if self._redactor.leaks(payload):
            raise self._invalid(
                f"cassette {cassette.name!r} holds something that looks like a secret; "
                "nothing was written"
            )
        self._root.mkdir(parents=True, exist_ok=True)
        target = self._path(cassette.name)
        partial = target.with_suffix(".json.partial")
        partial.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        partial.replace(target)

    def _path(self, name: str) -> Path:
        return self._root / f"{name}.json"

    def _payload(self, cassette: Cassette) -> dict[str, Any]:
        return {
            "format": self.FORMAT,
            "name": cassette.name,
            "provider": cassette.provider,
            "note": cassette.note,
            "interactions": [
                {
                    "request": {
                        "method": item.method,
                        "path": item.path,
                        "body": item.request_body,
                    },
                    "response": {"status": item.status, "body": item.response_body},
                }
                for item in cassette.interactions
            ],
        }

    def _build(self, name: str, data: Any) -> Cassette:
        if not isinstance(data, dict):
            raise self._invalid(f"cassette {name!r} is not a JSON object")
        unknown = sorted(data.keys() - self.KEYS)
        if unknown:
            raise self._invalid(f"cassette {name!r} has unknown keys {unknown}")
        if data.get("format") != self.FORMAT:
            raise self._invalid(f"cassette {name!r} is not format {self.FORMAT}")
        if data.get("name") != name:
            raise self._invalid(f"cassette file {name!r}.json names itself {data.get('name')!r}")
        try:
            return Cassette(
                name=name,
                provider=data["provider"],
                interactions=tuple(self._interaction(entry) for entry in data["interactions"]),
                note=data.get("note", ""),
            )
        except KeyError as error:
            raise self._invalid(f"cassette {name!r} is missing {error.args[0]!r}") from error
        except (TypeError, ValueError, AttributeError) as error:
            raise self._invalid(f"cassette {name!r}: {error}") from error

    def _interaction(self, entry: Any) -> CassetteInteraction:
        self._section(entry, self.ENTRY_KEYS)
        request = self._section(entry["request"], self.REQUEST_KEYS)
        response = self._section(entry["response"], self.RESPONSE_KEYS)
        return CassetteInteraction(
            method=request["method"],
            path=request["path"],
            request_body=request.get("body"),
            status=response["status"],
            response_body=response["body"],
        )

    @staticmethod
    def _section(value: Any, keys: frozenset[str]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.keys() - keys:
            raise ValueError(f"expected an object with only the keys {sorted(keys)}")
        return value

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="CASSETTE_INVALID", message=message, http_status=500)
