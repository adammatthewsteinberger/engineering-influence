# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds the run's artifact store from the settings: the database, or an S3-compatible bucket."""

from engineering_influence.infrastructure.object_storage.boto3_s3_client import Boto3S3Client
from engineering_influence.infrastructure.object_storage.s3_artifact_store import S3ArtifactStore
from engineering_influence.infrastructure.object_storage.s3_object_store import S3ObjectStore
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.artifact_store_factory_interface import (
    ArtifactStoreFactoryInterface,
)


class ArtifactStoreFactory(ArtifactStoreFactoryInterface):
    """`database` keeps the files in Postgres, as before. `s3` keeps each file as an object in `EI_S3_BUCKET`, which
    works with AWS S3 or with an S3-compatible service such as SeaweedFS (set `EI_S3_ENDPOINT_URL` to its address).
    The boto3 import happens only when the S3 store is chosen, so a database deployment does not need the `s3` extra.
    """

    def build(self, settings: AppSettings) -> SqlModelArtifactStore | S3ArtifactStore:
        if settings.artifact_store == "s3":
            return S3ArtifactStore(
                S3ObjectStore(Boto3S3Client(self._client(settings))), settings.s3_bucket
            )
        return SqlModelArtifactStore(settings.database_url)

    @staticmethod
    def _client(settings: AppSettings) -> object:
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
