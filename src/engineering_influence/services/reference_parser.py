# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finds Bible references such as ``John 3:16`` or ``1 Cor. 13:4-7`` in a text."""

import re
from typing import ClassVar

from engineering_influence.models.verse_ref import VerseRef
from engineering_influence.services.interfaces.reference_parser_interface import (
    ReferenceParserInterface,
)


class ReferenceParser(ReferenceParserInterface):
    """Protestant books, by their common names and abbreviations, with one chapter and a verse or a range of verses.

    A range runs within one chapter and is limited to ``MAX_RANGE`` verses, so a stray number cannot name a chapter's
    worth of text. A reference across chapters (``Gen 1:30-2:2``) is read as its first chapter only, which is the one
    the text names before the dash, and is not checked beyond that.
    """

    MAX_RANGE: ClassVar[int] = 30
    NAMES: ClassVar[dict[str, str]] = {
        "genesis": "GEN",
        "gen": "GEN",
        "exodus": "EXO",
        "exod": "EXO",
        "exo": "EXO",
        "ex": "EXO",
        "leviticus": "LEV",
        "lev": "LEV",
        "numbers": "NUM",
        "num": "NUM",
        "deuteronomy": "DEU",
        "deut": "DEU",
        "deu": "DEU",
        "joshua": "JOS",
        "josh": "JOS",
        "judges": "JDG",
        "judg": "JDG",
        "ruth": "RUT",
        "1 samuel": "1SA",
        "1 sam": "1SA",
        "2 samuel": "2SA",
        "2 sam": "2SA",
        "1 kings": "1KI",
        "1 kgs": "1KI",
        "2 kings": "2KI",
        "2 kgs": "2KI",
        "1 chronicles": "1CH",
        "1 chr": "1CH",
        "2 chronicles": "2CH",
        "2 chr": "2CH",
        "ezra": "EZR",
        "nehemiah": "NEH",
        "neh": "NEH",
        "esther": "EST",
        "esth": "EST",
        "job": "JOB",
        "psalms": "PSA",
        "psalm": "PSA",
        "psa": "PSA",
        "ps": "PSA",
        "proverbs": "PRO",
        "prov": "PRO",
        "pro": "PRO",
        "ecclesiastes": "ECC",
        "eccl": "ECC",
        "ecc": "ECC",
        "song of solomon": "SNG",
        "song of songs": "SNG",
        "song": "SNG",
        "isaiah": "ISA",
        "isa": "ISA",
        "jeremiah": "JER",
        "jer": "JER",
        "lamentations": "LAM",
        "lam": "LAM",
        "ezekiel": "EZK",
        "ezek": "EZK",
        "daniel": "DAN",
        "dan": "DAN",
        "hosea": "HOS",
        "hos": "HOS",
        "joel": "JOL",
        "amos": "AMO",
        "obadiah": "OBA",
        "obad": "OBA",
        "jonah": "JON",
        "jon": "JON",
        "micah": "MIC",
        "mic": "MIC",
        "nahum": "NAH",
        "nah": "NAH",
        "habakkuk": "HAB",
        "hab": "HAB",
        "zephaniah": "ZEP",
        "zeph": "ZEP",
        "haggai": "HAG",
        "hag": "HAG",
        "zechariah": "ZEC",
        "zech": "ZEC",
        "malachi": "MAL",
        "mal": "MAL",
        "matthew": "MAT",
        "matt": "MAT",
        "mat": "MAT",
        "mark": "MRK",
        "mrk": "MRK",
        "mk": "MRK",
        "luke": "LUK",
        "luk": "LUK",
        "lk": "LUK",
        "john": "JHN",
        "jhn": "JHN",
        "jn": "JHN",
        "acts": "ACT",
        "act": "ACT",
        "romans": "ROM",
        "rom": "ROM",
        "1 corinthians": "1CO",
        "1 cor": "1CO",
        "2 corinthians": "2CO",
        "2 cor": "2CO",
        "galatians": "GAL",
        "gal": "GAL",
        "ephesians": "EPH",
        "eph": "EPH",
        "philippians": "PHP",
        "phil": "PHP",
        "php": "PHP",
        "colossians": "COL",
        "col": "COL",
        "1 thessalonians": "1TH",
        "1 thess": "1TH",
        "2 thessalonians": "2TH",
        "2 thess": "2TH",
        "1 timothy": "1TI",
        "1 tim": "1TI",
        "2 timothy": "2TI",
        "2 tim": "2TI",
        "titus": "TIT",
        "tit": "TIT",
        "philemon": "PHM",
        "phlm": "PHM",
        "phm": "PHM",
        "hebrews": "HEB",
        "heb": "HEB",
        "james": "JAS",
        "jas": "JAS",
        "1 peter": "1PE",
        "1 pet": "1PE",
        "2 peter": "2PE",
        "2 pet": "2PE",
        "1 john": "1JN",
        "1 jn": "1JN",
        "2 john": "2JN",
        "2 jn": "2JN",
        "3 john": "3JN",
        "3 jn": "3JN",
        "jude": "JUD",
        "revelation": "REV",
        "rev": "REV",
    }
    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<![A-Za-z])(?P<book>(?:[1-3]\.?\s*)?[A-Za-z][A-Za-z ]*?)\.?\s+"
        r"(?P<chapter>\d{1,3}):(?P<first>\d{1,3})(?:\s*[\u2013-]\s*(?P<last>\d{1,3}))?(?![\d:])",
    )

    def find(self, text: str) -> tuple[tuple[int, int, tuple[VerseRef, ...]], ...]:
        """Each recognised reference, with the verses it names, in the order they appear."""
        found: list[tuple[int, int, tuple[VerseRef, ...]]] = []
        for match in self.PATTERN.finditer(text):
            named = self._code(match.group("book"))
            if named is None:
                continue
            code, offset = named
            chapter = int(match.group("chapter"))
            first = int(match.group("first"))
            last = int(match.group("last")) if match.group("last") else first
            if last < first or last - first + 1 > self.MAX_RANGE:
                continue
            try:
                verses = tuple(VerseRef(code, chapter, verse) for verse in range(first, last + 1))
            except ValueError:
                continue
            found.append((match.start("book") + offset, match.end(), verses))
        return tuple(found)

    def _code(self, name: str) -> tuple[str, int] | None:
        """The book code and where its name starts in the matched words, or None when no book is named.

        The matched words may carry some before the name ("as John"), so the name is the longest run of words at the
        end that is a book. The offset is where that run starts, so a reference's span begins at its book.
        """
        lowered = name.lower().replace(".", " ")
        starts = [match.start() for match in re.finditer(r"\S+", lowered)]
        for position, start in enumerate(starts):
            candidate = " ".join(lowered[start:].split())
            if candidate in self.NAMES:
                return self.NAMES[candidate], start
        return None
