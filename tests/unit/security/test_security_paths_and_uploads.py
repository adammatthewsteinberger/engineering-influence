"""Path confinement and upload inspection against hostile input."""

import io
import zipfile
from pathlib import Path

import pytest
from vibey_bootstrap.ingress.classifier import ClassificationResult

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.security.attachment_upload_inspector import (
    AttachmentUploadInspector,
)
from engineering_influence.infrastructure.security.confined_path_guard import ConfinedPathGuard

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF"


def make_zip(entries: int = 1) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index in range(entries):
            archive.writestr(f"{index}.txt", "x")
    return buffer.getvalue()


def test_relative_names_resolve_inside_the_root(tmp_path: Path) -> None:
    guard = ConfinedPathGuard()

    assert guard.confine("a/b.txt", tmp_path) == (tmp_path / "a" / "b.txt").resolve()


def test_absolute_paths_inside_the_root_are_allowed(tmp_path: Path) -> None:
    assert (
        ConfinedPathGuard().confine(tmp_path / "x.txt", tmp_path) == (tmp_path / "x.txt").resolve()
    )


@pytest.mark.parametrize("raw", ["../escape.txt", "a/../../escape.txt", "/etc/passwd"])
def test_paths_that_leave_the_root_are_refused(tmp_path: Path, raw: str) -> None:
    with pytest.raises(ApplicationError) as caught:
        ConfinedPathGuard().confine(raw, tmp_path)
    assert caught.value.code == "PATH_ESCAPE"
    assert str(tmp_path) not in caught.value.message


def test_a_symlink_cannot_smuggle_a_path_out(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(outside)

    with pytest.raises(ApplicationError):
        ConfinedPathGuard().confine("link/secret.txt", root)


def test_segments_lose_separators_and_traversal() -> None:
    guard = ConfinedPathGuard()

    assert guard.segment("../../x.pdf") == "x.pdf"
    assert guard.segment("a\x00b") == "a_b"
    assert guard.segment("") == "attachment"


def test_a_real_pdf_is_accepted() -> None:
    verdict = AttachmentUploadInspector().inspect("m.pdf", "application/pdf", PDF)

    assert verdict.accepted


def test_an_executable_renamed_to_pdf_is_refused() -> None:
    verdict = AttachmentUploadInspector().inspect("m.pdf", "application/pdf", b"MZ\x90\x00")

    assert not verdict.accepted
    assert verdict.reason is not None and "magic_byte" in verdict.reason


def test_unlisted_file_types_are_refused() -> None:
    verdict = AttachmentUploadInspector().inspect("notes.txt", "text/plain", b"abc")

    assert not verdict.accepted
    assert verdict.reason == "unsupported_extension: .txt"


def test_a_small_archive_is_accepted() -> None:
    assert AttachmentUploadInspector().inspect("a.zip", "application/zip", make_zip()).accepted


def test_an_archive_with_too_many_entries_is_a_zip_bomb() -> None:
    inspector = AttachmentUploadInspector(max_zip_entries=3)

    verdict = inspector.inspect("a.zip", "application/zip", make_zip(entries=5))

    assert not verdict.accepted
    assert verdict.reason == "zip_bomb"


def test_an_archive_that_expands_too_far_is_a_zip_bomb() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.txt", "0" * 100_000)
    inspector = AttachmentUploadInspector(max_zip_uncompressed_bytes=1_000)

    verdict = inspector.inspect("a.zip", "application/zip", buffer.getvalue())

    assert verdict.reason == "zip_bomb"


def test_a_corrupt_archive_is_refused() -> None:
    verdict = AttachmentUploadInspector().inspect(
        "a.zip", "application/zip", b"PK\x03\x04" + b"\x00" * 40
    )

    assert not verdict.accepted
    assert verdict.reason == "corrupt_archive"


def test_a_rejection_without_a_reason_still_has_one() -> None:
    class Rejecting:
        def classify(self, **_: object) -> ClassificationResult:
            return ClassificationResult(allowed=False, kind=None, reject_reason=None)

    inspector = AttachmentUploadInspector(classifier=Rejecting())  # type: ignore[arg-type]

    assert inspector.inspect("a.pdf", None, PDF).reason == "rejected"
