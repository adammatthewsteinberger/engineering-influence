"""Word and URL counting shared by the manuscript and release audits."""

import re


class TextStatistics:
    """Counts reader-visible words and source URLs."""

    WORD = re.compile(r"\b[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?\b")
    URL = re.compile(r"https?://[^\s)]+", re.IGNORECASE)

    def words(self, text: str) -> int:
        """Count words in plain text."""
        return len(self.WORD.findall(text))

    def urls(self, text: str) -> int:
        """Count http(s) URLs."""
        return len(self.URL.findall(text))

    def is_url(self, text: str) -> bool:
        """Return True when the whole text is one http(s) URL."""
        return self.URL.fullmatch(text) is not None

    def reader_words(self, markdown: str) -> int:
        """Count words without counting Markdown punctuation, code, or link targets."""
        text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
        return self.words(text)
