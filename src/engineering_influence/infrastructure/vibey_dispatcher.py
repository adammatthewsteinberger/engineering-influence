"""Adapter for registering engineering-influence handlers with vibey core."""

from importlib import import_module
from typing import Any

from engineering_influence.interfaces.handler_registry_port import HandlerRegistryPort


class VibeyHandlerRegistry(HandlerRegistryPort):
    """Own the third-party handler maps passed to vibey's dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def register_handler(self, kind: str, handler: Any) -> None:
        """Register a long-lived handler for a custom job kind."""
        if not kind.strip():
            raise ValueError("handler kind is required")
        self._handlers[kind] = handler

    def register_factory(self, kind: str, factory: Any) -> None:
        """Register a per-job factory for a custom job kind."""
        if not kind.strip():
            raise ValueError("factory kind is required")
        self._factories[kind] = factory

    def build_dispatcher(self) -> Any:
        """Build vibey's dispatcher with the registered custom maps."""
        dispatcher_module = import_module("vibey.application.job_dispatcher")
        return dispatcher_module.JobDispatcher(dict(self._handlers), dict(self._factories))
