# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An object store over an S3 client: a missing object reads as None, everything else is passed through."""

from engineering_influence.errors.missing_key_error import MissingKeyError
from engineering_influence.infrastructure.object_storage.interfaces.boto3_s3_client_interface import (
    Boto3S3ClientInterface,
)
from engineering_influence.infrastructure.object_storage.interfaces.s3_object_store_interface import (
    S3ObjectStoreInterface,
)


class S3ObjectStore(S3ObjectStoreInterface):
    """The bucket operations, over whichever S3 client the runtime gave it."""

    def __init__(self, client: Boto3S3ClientInterface) -> None:
        self._client = client

    def put(self, bucket: str, key: str, body: bytes) -> None:
        self._client.put_object(bucket, key, body)

    def get(self, bucket: str, key: str) -> bytes | None:
        try:
            return self._client.get_object(bucket, key)
        except MissingKeyError:
            return None

    def keys(self, bucket: str, prefix: str) -> list[str]:
        return sorted(self._client.list_keys(bucket, prefix))
