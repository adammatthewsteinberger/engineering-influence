# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""EI_OTLP_ENDPOINT reaches the settings; without it, nothing is exported."""

from collections.abc import Mapping

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader

DB = "postgresql+psycopg://svc:s3cretpw@db.internal:5432/ei"
MQ = "amqp://svc:rabbitpw@mq.internal:5672/"


class MappingSecrets(SecretProviderInterface):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if not self._values.get(name, "").strip():
            raise ApplicationError("SECRET_MISSING", f"{name} is not configured", http_status=503)
        return self._values[name].strip()


def load(extra: Mapping[str, str]) -> str:
    values = {"EI_DATABASE_URL": DB, "EI_RABBITMQ_URL": MQ, "EI_API_KEYS": "k" * 30, **extra}
    return EnvironmentSettingsLoader(MappingSecrets(values), values).load().otlp_endpoint


def test_the_endpoint_is_read_from_the_environment() -> None:
    assert load({"EI_OTLP_ENDPOINT": "http://tempo.ei.svc:4318"}) == "http://tempo.ei.svc:4318"


def test_no_endpoint_means_no_export() -> None:
    assert load({}) == ""
