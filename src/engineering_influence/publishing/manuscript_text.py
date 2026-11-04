"""Parsing helpers for Markdown manuscript files."""

import re


class ManuscriptText:
    """Titles, bodies, and prose paragraphs of a Markdown source file."""

    TITLE = re.compile(r"^\s*#\s+(.+?)\s*$")
    CHAPTER_PREFIX = re.compile(
        r"^Chapter\s+(?:\d+|[A-Z][a-z]+(?:-[a-z]+)?)\s*[:.]\s*", re.IGNORECASE
    )

    def normalise(self, text: str) -> str:
        """Lowercase and keep only letters and digits."""
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def title_and_body(self, text: str) -> tuple[str, str] | None:
        """Split on the level-1 title; None when the first line is not one."""
        lines = text.splitlines()
        if not lines:
            return None
        match = self.TITLE.match(lines[0])
        if not match:
            return None
        title = self.CHAPTER_PREFIX.sub("", match.group(1)).strip()
        return title, "\n".join(lines[1:]).strip()

    def paragraphs(self, body: str) -> list[str]:
        """Prose paragraphs, skipping blocks made only of block quotes (epigraphs)."""
        result: list[str] = []
        for block in re.split(r"\n\s*\n", body.strip()):
            block = block.strip()
            if not block:
                continue
            if all(
                not line.strip() or line.lstrip().startswith(">") for line in block.splitlines()
            ):
                continue
            result.append(block)
        return result
