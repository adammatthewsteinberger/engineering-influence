# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a novel's chapters against its story bible, with no model, and reports where they disagree."""

import re
from typing import ClassVar

from engineering_influence.models.continuity_finding import ContinuityFinding
from engineering_influence.models.story_bible import StoryBible
from engineering_influence.models.story_character import StoryCharacter
from engineering_influence.services.interfaces.continuity_checker_interface import (
    ContinuityCheckerInterface,
)


class ContinuityChecker(ContinuityCheckerInterface):
    """Three checks, each of which can be wrong in a known way, so a finding is a question and not a verdict.

    **Spelling.** A capitalised word that is one edit (a letter changed, added, dropped or swapped with its neighbour)
    from a known name or place, and is not one itself, is reported: ``Katharine`` where the bible has ``Katherine``.
    A word the chapter also writes in lower case is a common word and is left alone, and names shorter than
    ``MIN_LENGTH`` are never compared, because three letters are one edit from too many words. A new character who
    happens to be named like an old one is the false positive; add them to the bible.

    **Age.** An age stated in one of three shapes (``Ana, 34,``; ``Ana was 34 years old``; ``a 34-year-old Ana``) must
    lie between the bible's age and that age plus the story's span. Any other way of saying an age is not read.

    **Timeline.** The first mention of each dated event, in reading order, must not fall after a later event's.
    A flashback is a good reason for a finding to be wrong.

    Chapters are untrusted text and are only ever searched; nothing here runs them.
    """

    MIN_LENGTH: ClassVar[int] = 4
    MAX_CHAPTERS: ClassVar[int] = 200
    MAX_FINDINGS: ClassVar[int] = 200
    WORD: ClassVar[re.Pattern[str]] = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")

    def check(self, bible: StoryBible, chapters: tuple[str, ...]) -> tuple[ContinuityFinding, ...]:
        """The findings, in chapter order, for chapters numbered from 1 in the order given."""
        if not isinstance(chapters, tuple) or not 1 <= len(chapters) <= self.MAX_CHAPTERS:
            raise ValueError(f"check one to {self.MAX_CHAPTERS} chapters at a time")
        if any(not isinstance(text, str) for text in chapters):
            raise TypeError("a chapter is text")
        found: list[ContinuityFinding] = []
        for number, text in enumerate(chapters, start=1):
            found += self._spellings(bible, number, text)
            found += self._ages(bible, number, text)
        found += self._timeline(bible, chapters)
        order = {kind: position for position, kind in enumerate(ContinuityFinding.KINDS)}
        found.sort(key=lambda item: (item.chapter, order[item.kind]))
        return tuple(found[: self.MAX_FINDINGS])

    def _spellings(self, bible: StoryBible, number: int, text: str) -> list[ContinuityFinding]:
        known = self._known_words(bible)
        words = self.WORD.findall(text)
        common = {word.casefold() for word in words if word[0].islower()}
        seen: set[str] = set()
        out: list[ContinuityFinding] = []
        for word in words:
            folded = word.casefold()
            if (
                not word[0].isupper()
                or len(word) < self.MIN_LENGTH
                or folded in known
                or folded in common
                or folded in seen
            ):
                continue
            seen.add(folded)
            for candidate, (kind, shown) in known.items():
                if len(candidate) >= self.MIN_LENGTH and self._one_edit(folded, candidate):
                    out.append(
                        ContinuityFinding(
                            number,
                            kind,
                            shown,
                            word,
                            f"the chapter writes {word}; the bible has {shown}",
                        )
                    )
                    break
        return out

    def _known_words(self, bible: StoryBible) -> dict[str, tuple[str, str]]:
        known: dict[str, tuple[str, str]] = {}
        for character in bible.characters:
            for form in character.forms():
                for word in self.WORD.findall(form):
                    known.setdefault(word.casefold(), ("name", word))
        for place in bible.places:
            for word in self.WORD.findall(place):
                known.setdefault(word.casefold(), ("place", word))
        return known

    @staticmethod
    def _one_edit(left: str, right: str) -> bool:
        if len(left) == len(right):
            apart = [index for index in range(len(left)) if left[index] != right[index]]
            if len(apart) == 1:
                return True
            return (
                len(apart) == 2
                and apart[1] == apart[0] + 1
                and left[apart[0]] == right[apart[1]]
                and left[apart[1]] == right[apart[0]]
            )
        short, long = (left, right) if len(left) < len(right) else (right, left)
        index = 0
        while index < len(short) and short[index] == long[index]:
            index += 1
        return short[index:] == long[index + 1 :]

    def _ages(self, bible: StoryBible, number: int, text: str) -> list[ContinuityFinding]:
        out: list[ContinuityFinding] = []
        for character in bible.characters:
            if character.age is None:
                continue
            low, high = character.age, character.age + bible.span_years
            said: set[int] = set()
            for age in self._stated_ages(character, text):
                if low <= age <= high or age in said:
                    continue
                said.add(age)
                allowed = str(low) if low == high else f"{low} to {high}"
                out.append(
                    ContinuityFinding(
                        number,
                        "age",
                        allowed,
                        str(age),
                        f"{character.name} is {age} here; the bible has {allowed}",
                    )
                )
        return out

    @staticmethod
    def _stated_ages(character: StoryCharacter, text: str) -> list[int]:
        forms = {*character.forms(), character.name.split()[0]}
        ages: list[tuple[int, int]] = []
        for form in forms:
            name = re.escape(form)
            patterns = (
                rf"(?<!\w){name},\s*(\d{{1,3}}),",
                rf"(?<!\w){name}\s+(?:is|was|turned|turns)\s+(\d{{1,3}})\s+years?\s+old",
                rf"(\d{{1,3}})[-\s]year[-\s]old\s+{name}(?!\w)",
            )
            for pattern in patterns:
                ages += [(match.start(), int(match[1])) for match in re.finditer(pattern, text)]
        return [age for _, age in sorted(ages)]

    @staticmethod
    def _timeline(bible: StoryBible, chapters: tuple[str, ...]) -> list[ContinuityFinding]:
        mentions: list[tuple[int, int, int]] = []
        for index, event in enumerate(bible.timeline):
            pattern = re.compile(rf"(?<!\w){re.escape(event.label)}(?!\w)", re.IGNORECASE)
            for number, text in enumerate(chapters, start=1):
                match = pattern.search(text)
                if match:
                    mentions.append((number, match.start(), index))
                    break
        out: list[ContinuityFinding] = []
        latest = None
        for number, _, index in sorted(mentions):
            event = bible.timeline[index]
            if latest is not None and event.when < latest.when:
                out.append(
                    ContinuityFinding(
                        number,
                        "timeline",
                        f"{event.label} before {latest.label}",
                        f"{event.label} after {latest.label}",
                        f"'{event.label}' comes after '{latest.label}' in the chapters but before it in the bible",
                    )
                )
            else:
                latest = event
        return out
