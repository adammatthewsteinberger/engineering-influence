"""Vibey custom-handler registration tests."""

import pytest

from engineering_influence.infrastructure import VibeyHandlerRegistry


class HandlerFake:
    """Marker handler used to inspect dispatcher registration."""


def test_registry_builds_vibey_dispatcher_with_custom_handler() -> None:
    handler = HandlerFake()
    registry = VibeyHandlerRegistry()
    registry.register_handler("pipeline.thesis", handler)
    factory = HandlerFake()
    registry.register_factory("pipeline.book", factory)

    dispatcher = registry.build_dispatcher()

    assert dispatcher._handlers == {"pipeline.thesis": handler}
    assert dispatcher._factories == {"pipeline.book": factory}


@pytest.mark.parametrize("method", ["register_handler", "register_factory"])
def test_registry_requires_kind(method: str) -> None:
    registry = VibeyHandlerRegistry()
    with pytest.raises(ValueError, match="kind is required"):
        getattr(registry, method)("", object())
