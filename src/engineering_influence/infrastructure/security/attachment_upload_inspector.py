# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Upload inspection: extension, type, size, magic bytes and zip bombs."""

import io
import zipfile

from vibey_bootstrap.exceptions import ZipBombError
from vibey_bootstrap.ingress.classifier import AttachmentClassifier
from vibey_bootstrap.ingress.zip_safety import enforce_zip_safety_limits

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.interfaces.upload_inspector_port import UploadInspectorPort


class AttachmentUploadInspector(UploadInspectorPort):
    """Run the four ingress gates, then inspect archives before anything extracts them."""

    def __init__(
        self,
        classifier: AttachmentClassifier | None = None,
        max_zip_entries: int = 100,
        max_zip_uncompressed_bytes: int = 524_288_000,
    ) -> None:
        self._classifier = classifier or AttachmentClassifier()
        self._max_entries = max_zip_entries
        self._max_bytes = max_zip_uncompressed_bytes

    def inspect(self, filename: str, content_type: str | None, content: bytes) -> SecurityVerdict:
        """Return accept, or reject with a stable reason code."""
        result = self._classifier.classify(
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            content=content,
        )
        if not result.allowed:
            return SecurityVerdict.reject(result.reject_reason or "rejected")
        if result.kind == "zip":
            return self._inspect_archive(filename, content)
        return SecurityVerdict.accept()

    def _inspect_archive(self, filename: str, content: bytes) -> SecurityVerdict:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                enforce_zip_safety_limits(
                    archive,
                    filename=filename,
                    max_entries=self._max_entries,
                    max_uncompressed_bytes=self._max_bytes,
                )
        except ZipBombError:
            return SecurityVerdict.reject("zip_bomb")
        except zipfile.BadZipFile:
            return SecurityVerdict.reject("corrupt_archive")
        return SecurityVerdict.accept()
