# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The artifact store is the database unless EI_ARTIFACT_STORE says s3, and an S3 store needs its bucket and keys."""

from collections.abc import Mapping

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.object_storage.s3_artifact_store import S3ArtifactStore
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.artifact_store_factory import ArtifactStoreFactory
from engineering_influence.runtime.environment_settings_loader import EnvironmentSettingsLoader

DB = "postgresql+psycopg://svc:s3cretpw@db.internal:5432/ei"
MQ = "amqp://svc:rabbitpw@mq.internal:5672/"
S3_SECRETS = {
    "EI_S3_ACCESS_KEY_ID": "AKIAFAKEFAKEFAKE",
    "EI_S3_SECRET_ACCESS_KEY": "fake-secret-value",
}


class MappingSecrets(SecretProviderInterface):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if not self._values.get(name, "").strip():
            raise ApplicationError(
                "SECRET_MISSING", f"required secret {name} is not configured", http_status=503
            )
        return self._values[name].strip()


def load(env: Mapping[str, str]) -> AppSettings:
    values = {"EI_DATABASE_URL": DB, "EI_RABBITMQ_URL": MQ, **S3_SECRETS, **env}
    return EnvironmentSettingsLoader(MappingSecrets(values), values).load()


def test_the_database_is_the_artifact_store_by_default() -> None:
    settings = load({})
    assert settings.artifact_store == "database"
    assert isinstance(ArtifactStoreFactory().build(settings), SqlModelArtifactStore)


def test_an_s3_store_needs_its_bucket() -> None:
    with pytest.raises(ValueError, match="EI_S3_BUCKET is required"):
        load({"EI_ARTIFACT_STORE": "s3"})


def test_an_unknown_artifact_store_is_refused() -> None:
    with pytest.raises(ValueError, match="EI_ARTIFACT_STORE must be database or s3"):
        load({"EI_ARTIFACT_STORE": "ftp"})


def test_an_s3_store_reads_its_bucket_endpoint_region_and_keys() -> None:
    settings = load(
        {
            "EI_ARTIFACT_STORE": "s3",
            "EI_S3_BUCKET": "ei-artifacts",
            "EI_S3_ENDPOINT_URL": "http://seaweedfs.ei.svc:8333",
            "EI_S3_REGION": "us-east-2",
        }
    )
    assert (settings.s3_bucket, settings.s3_endpoint_url, settings.s3_region) == (
        "ei-artifacts",
        "http://seaweedfs.ei.svc:8333",
        "us-east-2",
    )
    assert settings.s3_access_key_id == "AKIAFAKEFAKEFAKE"
    assert "fake-secret-value" not in repr(settings)


def test_an_s3_store_is_built_over_a_boto3_client_without_contacting_it() -> None:
    settings = load(
        {
            "EI_ARTIFACT_STORE": "s3",
            "EI_S3_BUCKET": "ei-artifacts",
            "EI_S3_ENDPOINT_URL": "http://127.0.0.1:9",
        }
    )
    assert isinstance(ArtifactStoreFactory().build(settings), S3ArtifactStore)
