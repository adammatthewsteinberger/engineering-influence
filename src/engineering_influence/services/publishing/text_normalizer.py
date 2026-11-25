# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Text normalization used to compare printed text with configured text."""

import re
import unicodedata

from engineering_influence.services.publishing.interfaces.text_normalizer_interface import (
    TextNormalizerInterface,
)


class TextNormalizer(TextNormalizerInterface):
    """Lowercases, folds quotes, and strips punctuation and whitespace."""

    def normalize(self, text: str) -> str:
        """Return a comparison key for the text."""
        folded = unicodedata.normalize("NFKC", text)
        folded = folded.replace("’", "'").replace("‘", "'")
        folded = folded.replace("“", '"').replace("”", '"')
        return re.sub(r"[^\w']+", "", folded.lower())
