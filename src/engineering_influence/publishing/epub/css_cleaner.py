# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Removes rules that hide elements from an ebook stylesheet."""

import re


class CssCleaner:
    """Nothing in an ebook needs to be hidden."""

    HIDDEN_RULE = re.compile(r"[^{}]*\{[^{}]*display\s*:\s*none[^{}]*\}\s*")

    def strip_hidden_rules(self, css: str) -> str:
        """Drop every rule that hides an element.

        Kindle's converter cannot resolve a contents link whose target is hidden, and reads a
        rule like ``h2 br { display: none }`` as hiding the heading.
        """
        return self.HIDDEN_RULE.sub("", css)
