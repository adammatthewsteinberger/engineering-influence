# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The boto3 wrapper maps a missing key to MissingKeyError, passes every other error through, and pages through listings."""

from typing import Any

import pytest
from botocore.exceptions import ClientError

from engineering_influence.errors.missing_key_error import MissingKeyError
from engineering_influence.infrastructure.object_storage.boto3_s3_client import Boto3S3Client


class Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class Paginator:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages

    def paginate(self, **kwargs: str) -> list[dict[str, Any]]:
        self.kwargs = kwargs
        return self._pages


class FakeBoto3:
    """Answers the calls the wrapper makes, as boto3 does: the body is a stream and a missing key is a ClientError."""

    def __init__(
        self, error_code: str | None = None, pages: list[dict[str, Any]] | None = None
    ) -> None:
        self.error_code = error_code
        self.pages = pages or [{"Contents": [{"Key": "ei/a.md"}]}]
        self.puts: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.puts.append(kwargs)

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.error_code is not None:
            raise ClientError({"Error": {"Code": self.error_code, "Message": "x"}}, "GetObject")
        return {"Body": Body(b"bytes")}

    def get_paginator(self, name: str) -> Paginator:
        assert name == "list_objects_v2"
        return Paginator(self.pages)


def test_a_put_names_the_bucket_key_and_body() -> None:
    client = FakeBoto3()
    Boto3S3Client(client).put_object("ei", "runs/a.md", b"x")
    assert client.puts == [{"Bucket": "ei", "Key": "runs/a.md", "Body": b"x"}]


def test_a_get_returns_the_body() -> None:
    assert Boto3S3Client(FakeBoto3()).get_object("ei", "a.md") == b"bytes"


@pytest.mark.parametrize("code", ["NoSuchKey", "404"])
def test_a_missing_key_is_reported_as_missing(code: str) -> None:
    with pytest.raises(MissingKeyError):
        Boto3S3Client(FakeBoto3(error_code=code)).get_object("ei", "a.md")


def test_any_other_error_is_passed_through() -> None:
    with pytest.raises(ClientError):
        Boto3S3Client(FakeBoto3(error_code="AccessDenied")).get_object("ei", "a.md")


def test_a_listing_reads_every_page_and_an_empty_page_adds_nothing() -> None:
    client = FakeBoto3(
        pages=[{"Contents": [{"Key": "ei/a.md"}]}, {}, {"Contents": [{"Key": "ei/b.md"}]}]
    )
    assert Boto3S3Client(client).list_keys("ei", "ei/") == ["ei/a.md", "ei/b.md"]
