"""Running heads for long chapter titles."""

import re
from itertools import accumulate


class RunningHead:
    """Uses the main clause of a long title."""

    DANGLING = frozenset(
        {
            "a",
            "an",
            "the",
            "of",
            "and",
            "or",
            "to",
            "in",
            "for",
            "with",
            "that",
            "from",
            "when",
            "is",
        }
    )

    def make(self, title: str, limit: int = 42) -> str:
        """Return the title, or its main clause when the title is longer than the limit."""
        if len(title) <= limit:
            return title
        head = re.split(r":\s", title, maxsplit=1)[0]
        if len(head) <= limit:
            return head
        clause = head.split(", ", 1)[0]
        if 12 <= len(clause) <= limit:
            return clause
        words = head.split()
        # Cumulative joined length of the first n words is accumulate(len + 1) - 1; lengths only
        # grow, so the words that fit are a prefix.
        totals = accumulate(len(word) + 1 for word in words)
        kept = [word for word, total in zip(words, totals, strict=True) if total - 1 <= limit]
        while kept and kept[-1].lower() in self.DANGLING:
            kept.pop()
        return " ".join(kept)
