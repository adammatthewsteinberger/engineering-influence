"""Records the size of every run of text a render draws."""


class TextRecorder:
    """Per-render state that replaces a module-level list, so renders never share it."""

    def __init__(self) -> None:
        self._sizes: list[int] = []

    def record(self, size: int) -> None:
        """Note one run of text at an em size in pixels."""
        self._sizes.append(size)

    def smallest(self) -> int | None:
        """The smallest size drawn, or None when nothing was drawn."""
        return min(self._sizes) if self._sizes else None
