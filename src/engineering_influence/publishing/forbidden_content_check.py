"""Rejects printed content that must never reach a finished book."""

import re

from engineering_influence.publishing.text_normalizer import TextNormalizer


class ForbiddenContentCheck:
    """Dashes, placeholder markers, the word Draft, and the Edition line."""

    MARKERS = ("[CALLOUT", "[/CALLOUT", "[TESTIMONY", "[PLACEHOLDER", "[ILLUSTRATION")

    def run(self, texts: list[str], edition: str) -> list[str]:
        """Return a problem for each forbidden item found in the page texts."""
        problems: list[str] = []
        full = "\n".join(texts)
        for label, pattern in (("em dash", "—"), ("en dash", "–")):
            for index, text in enumerate(texts):
                if pattern in text:
                    problems.append(f"page {index + 1}: contains an {label}")
                    break
        for marker in self.MARKERS:
            if marker in full:
                problems.append(f"marker {marker!r} printed in the book")
        if re.search(r"\bDraft\b", full):
            problems.append("the word 'Draft' appears in the book")
        normalizer = TextNormalizer()
        if edition and normalizer.normalize(edition) not in normalizer.normalize(full):
            problems.append(f"edition line {edition!r} not found")
        if "Edition" not in edition:
            problems.append("the edition in the config does not say Edition")
        return problems
