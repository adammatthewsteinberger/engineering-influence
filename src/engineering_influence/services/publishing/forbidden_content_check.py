# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rejects printed content that must never reach a finished book."""

import re

from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.services.publishing.interfaces.forbidden_content_check_interface import (
    ForbiddenContentCheckInterface,
)
from engineering_influence.services.publishing.text_normalizer import TextNormalizer


class ForbiddenContentCheck(ForbiddenContentCheckInterface):
    """Dashes, placeholder markers, the word Draft, and the Edition line, under a text policy."""

    DIALOGUE = re.compile("\u201c[^\u201d]{0,500}\u201d")
    MARKERS = ("[CALLOUT", "[/CALLOUT", "[TESTIMONY", "[PLACEHOLDER", "[ILLUSTRATION")

    def run(self, texts: list[str], edition: str, policy: TextPolicy) -> list[str]:
        """Return a problem for each forbidden item found in the page texts."""
        problems: list[str] = []
        full = "\n".join(texts)
        dashes = (
            [("en dash", "–")] if policy.allows_em_dash else [("em dash", "—"), ("en dash", "–")]
        )
        for label, pattern in dashes:
            for index, text in enumerate(texts):
                if pattern in text:
                    problems.append(f"page {index + 1}: contains an {label}")
                    break
        for marker in self.MARKERS:
            if marker in full:
                problems.append(f"marker {marker!r} printed in the book")
        prose = self.DIALOGUE.sub(" ", full) if policy.allows_draft_in_dialogue else full
        if re.search(r"\bDraft\b", prose):
            problems.append("the word 'Draft' appears in the book")
        normalizer = TextNormalizer()
        if edition and normalizer.normalize(edition) not in normalizer.normalize(full):
            problems.append(f"edition line {edition!r} not found")
        if "Edition" not in edition:
            problems.append("the edition in the config does not say Edition")
        return problems
