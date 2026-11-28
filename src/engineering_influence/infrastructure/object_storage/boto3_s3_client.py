# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The S3 client port over a boto3 client, which AWS S3 and S3-compatible services such as SeaweedFS answer."""

from typing import Any

from botocore.exceptions import ClientError

from engineering_influence.errors.missing_key_error import MissingKeyError
from engineering_influence.infrastructure.object_storage.interfaces.boto3_s3_client_interface import (
    Boto3S3ClientInterface,
)


class Boto3S3Client(Boto3S3ClientInterface):
    """Wraps a boto3 `s3` client. The client is created by the runtime, so the endpoint and credentials stay there."""

    MISSING_CODES = frozenset({"NoSuchKey", "404"})

    def __init__(self, client: Any) -> None:
        """Remember the boto3 S3 client the runtime created."""
        self._client = client

    def put_object(self, bucket: str, key: str, body: bytes) -> None:
        """Store the body under the key in the bucket."""
        self._client.put_object(Bucket=bucket, Key=key, Body=body)

    def get_object(self, bucket: str, key: str) -> bytes:
        """The bytes stored under the key; raise MissingKeyError when the key is not there."""
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in self.MISSING_CODES:
                raise MissingKeyError(key) from error
            raise
        data: bytes = response["Body"].read()
        return data

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        """Every key in the bucket that starts with the prefix, across all result pages."""
        keys: list[str] = []
        for page in self._client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix
        ):
            keys.extend(item["Key"] for item in page.get("Contents", []))
        return keys
