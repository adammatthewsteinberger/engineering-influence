# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Patterns shared by the EPUB cleanup and verification classes."""

import re


class XhtmlPatterns:
    """Headings, ids, and the empty blocks TeX4ht leaves behind."""

    HEADING = re.compile(r"<h([1-6])\b([^>]*)>(.*?)</h\1>", re.DOTALL)
    ID = re.compile(r"\bid=['\"]([^'\"]+)['\"]")
    EMPTY_BLOCK = re.compile(
        r"<p\b[^>]*>\s*</p>|<div class=.crosslinks.>\s*(?:<p\b[^>]*>\s*</p>)?\s*</div>"
    )
    EMPTY_ANCHOR = re.compile(r"<a id=(['\"])([^'\"]+)\1>\s*</a>")
    CHAPTER_HEAD_BR = re.compile(
        r"(<h2\b[^>]*\bclass=['\"]chapterHead['\"][^>]*>(?:(?!</h2>).)*?)<br\s*/?>", re.DOTALL
    )
    NAV_ITEM = re.compile(r"<item\b(?=[^>]*properties=.nav.)[^>]*href=.([^'\"]+)")
