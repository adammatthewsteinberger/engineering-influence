"""One chapter as LaTeX."""

from engineering_influence.publishing.typesetting.chapter import Chapter
from engineering_influence.publishing.typesetting.markdown_latex_converter import (
    MarkdownLatexConverter,
)
from engineering_influence.publishing.typesetting.tex_text import TexText


class ChapterTex:
    """Heading, table-of-contents entry, running head, epigraph, and body."""

    def __init__(self) -> None:
        self._tex = TexText()
        self._converter = MarkdownLatexConverter()

    def render(self, chapter: Chapter, number_chapters: bool = True) -> str:
        """Return the chapter's LaTeX."""
        text = self._tex.text
        title = text(chapter.title)
        numbered_title = (
            text(f"Chapter {chapter.number}: {chapter.title}") if chapter.number else title
        )
        toc_title = (
            text(str(chapter.number)) + r"\hspace{1em}" + text(chapter.title)
            if chapter.number
            else title
        )
        short = text(chapter.short)
        parts = []
        if chapter.kind == "chapter" and number_chapters:
            parts.append(f"\\chapter{{{title}}}\n\\chapterheadmark{{{short}}}\n")
        elif chapter.kind == "chapter":
            parts.append(
                f"\\chapter*{{{title}}}\n\\addcontentsline{{toc}}{{chapter}}{{{title}}}\n"
                f"\\chapterheadmark{{{short}}}\n"
            )
        else:
            parts.append(
                f"\\chapter*{{{numbered_title}}}\n"
                f"\\addcontentsline{{toc}}{{chapter}}{{{toc_title}}}\n"
                f"\\chapterheadmark{{{short}}}\n"
            )
        if chapter.epigraph:
            quote, source = chapter.epigraph
            parts.append(
                f"\\begin{{chapterepigraph}}{{{text(source)}}}\n{text(quote)}\n"
                "\\end{chapterepigraph}\n"
            )
        parts.append(self._converter.convert(chapter.body, style=chapter.style))
        return "".join(parts)
