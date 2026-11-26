# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The webhook settings: off by default, receivers must be https, the secret is required once a receiver is set and is
never printed."""

from collections.abc import Mapping

import pytest

from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader

BASE = {"EI_DATABASE_URL": "postgresql://db", "EI_RABBITMQ_URL": "amqp://mq"}


class Secrets(SecretProviderInterface):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if name not in self._values:
            raise ValueError(f"{name} is required")
        return self._values[name]


def load(env: Mapping[str, str]):  # type: ignore[no-untyped-def]
    return EnvironmentSettingsLoader(Secrets(env), env).load()


def test_webhooks_are_off_by_default() -> None:
    settings = load(BASE)
    assert settings.webhook_urls == ()
    assert settings.webhook_secret == ""
    assert settings.webhook_interval_seconds == 5.0


def test_receivers_and_the_secret_are_read_together() -> None:
    env = {
        **BASE,
        "EI_WEBHOOK_URLS": " https://a.example/in , https://b.example/in ,",
        "EI_WEBHOOK_SECRET": "s3cret",
        "EI_WEBHOOK_INTERVAL_SECONDS": "2.5",
    }
    settings = load(env)
    assert settings.webhook_urls == ("https://a.example/in", "https://b.example/in")
    assert settings.webhook_secret == "s3cret"
    assert settings.webhook_interval_seconds == 2.5


def test_a_receiver_without_a_secret_stops_startup() -> None:
    with pytest.raises(ValueError, match="EI_WEBHOOK_SECRET is required"):
        load({**BASE, "EI_WEBHOOK_URLS": "https://a.example/in"})


def test_a_receiver_that_is_not_https_is_refused() -> None:
    with pytest.raises(ValueError, match="https:// addresses only"):
        load({**BASE, "EI_WEBHOOK_URLS": "http://a.example/in", "EI_WEBHOOK_SECRET": "x"})


def test_the_settings_never_print_the_secret() -> None:
    settings = load(
        {**BASE, "EI_WEBHOOK_URLS": "https://a.example/in", "EI_WEBHOOK_SECRET": "s3cret"}
    )
    assert "s3cret" not in repr(settings)
