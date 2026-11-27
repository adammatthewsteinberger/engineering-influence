# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The S3 artifact store keeps a run's files as objects, write-once, and reads them back by run and name."""

import pytest

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.errors.missing_key_error import MissingKeyError
from engineering_influence.infrastructure.object_storage.interfaces.boto3_s3_client_interface import (
    Boto3S3ClientInterface,
)
from engineering_influence.infrastructure.object_storage.s3_artifact_store import S3ArtifactStore
from engineering_influence.infrastructure.object_storage.s3_object_store import S3ObjectStore


class MemoryS3(Boto3S3ClientInterface):
    """An in-memory S3 client: the calls the adapter makes, and nothing else."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, bucket: str, key: str, body: bytes) -> None:
        self.objects[f"{bucket}/{key}"] = body

    def get_object(self, bucket: str, key: str) -> bytes:
        if f"{bucket}/{key}" not in self.objects:
            raise MissingKeyError(key)
        return self.objects[f"{bucket}/{key}"]

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        start = f"{bucket}/"
        return [name[len(start) :] for name in self.objects if name.startswith(start + prefix)]


def store(client: MemoryS3 | None = None, prefix: str = "runs") -> S3ArtifactStore:
    return S3ArtifactStore(S3ObjectStore(client or MemoryS3()), "ei", prefix)


def test_an_artifact_is_read_back_by_its_run_and_name() -> None:
    artifacts = store()
    artifacts.put("run-1", "draft/chapter-01.md", b"text")
    assert artifacts.get("run-1", "draft/chapter-01.md") == b"text"


def test_a_missing_artifact_reads_as_none() -> None:
    assert store().get("run-1", "absent.md") is None


def test_the_digest_is_the_sha256_of_the_bytes() -> None:
    import hashlib

    assert store().put("run-1", "a.md", b"text") == hashlib.sha256(b"text").hexdigest()


def test_the_same_bytes_again_are_accepted_and_different_bytes_are_refused() -> None:
    artifacts = store()
    artifacts.put("run-1", "a.md", b"one")
    artifacts.put("run-1", "a.md", b"one")
    with pytest.raises(ArtifactConflictError):
        artifacts.put("run-1", "a.md", b"two")
    assert artifacts.get("run-1", "a.md") == b"one"


def test_names_list_one_run_only_and_sort() -> None:
    artifacts = store()
    artifacts.put("run-1", "b.md", b"b")
    artifacts.put("run-1", "a/c.md", b"c")
    artifacts.put("run-2", "z.md", b"z")
    assert artifacts.names("run-1") == ["a/c.md", "b.md"]
    assert artifacts.names("run-3") == []


def test_the_prefix_is_stored_without_its_slashes() -> None:
    client = MemoryS3()
    store(client, prefix="/runs/").put("run-1", "a.md", b"a")
    assert "ei/runs/run-1/a.md" in client.objects


def test_a_bucket_and_prefix_are_required() -> None:
    with pytest.raises(ValueError, match="needs a bucket and a prefix"):
        S3ArtifactStore(S3ObjectStore(MemoryS3()), " ", "runs")
    with pytest.raises(ValueError, match="needs a bucket and a prefix"):
        S3ArtifactStore(S3ObjectStore(MemoryS3()), "ei", " ")


def test_a_run_id_that_climbs_out_of_the_prefix_is_refused() -> None:
    with pytest.raises(ValueError):
        store().put("../other", "a.md", b"a")
