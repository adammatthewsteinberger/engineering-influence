"""Running heads, chapter and book loading, metadata text, and chapter LaTeX."""

from pathlib import Path

import pytest

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.typesetting.book_loader import BookLoader
from engineering_influence.publishing.typesetting.chapter import Chapter
from engineering_influence.publishing.typesetting.chapter_loader import ChapterLoader
from engineering_influence.publishing.typesetting.chapter_tex import ChapterTex
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError
from engineering_influence.publishing.typesetting.running_head import RunningHead
from engineering_influence.publishing.typesetting.tex_text import TexText


def test_running_head_prefers_the_main_clause() -> None:
    head = RunningHead()
    assert head.make("Short title") == "Short title"
    assert head.make("A Main Clause: and a very long subtitle that goes on") == "A Main Clause"
    long_title = "The Case for Attention, Which Rewards Patience When Everything Else Fails Today"
    assert head.make(long_title) == "The Case for Attention"


def test_running_head_trims_words_and_dangling_function_words() -> None:
    head = RunningHead()
    assert head.make("Alpha beta gamma delta epsilon zeta eta theta iota kappa") == (
        "Alpha beta gamma delta epsilon zeta eta"
    )
    assert head.make("Alpha beta gamma delta epsilon zeta a of the end more words") == (
        "Alpha beta gamma delta epsilon zeta"
    )
    assert head.make("Short, a b c d e f g h i j k l m n o p q r s t u v w x y z") == (
        "Short, a b c d e f g h i j k l m n o p q r"
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def loader(root: Path, strict: bool = True) -> ChapterLoader:
    return ChapterLoader(PathRelativizer(root), strict)


def test_chapter_loader_reads_title_body_and_epigraph(tmp_path: Path) -> None:
    path = write(
        tmp_path / "c.md",
        "# Chapter 3: The Road\n\n> Walk on.\n>\n> A Poet\n\nBody text.\n",
    )
    chapter = loader(tmp_path).load(path, "chapter", "prose", None)
    assert (chapter.title, chapter.short, chapter.body) == ("The Road", "The Road", "Body text.")
    assert chapter.epigraph == ("Walk on.", "A Poet")


def test_epigraph_needs_a_chapter_and_a_short_attribution(tmp_path: Path) -> None:
    quote = "# T\n\n> Walk on.\n>\n> {}\n\nBody.\n"
    front = write(tmp_path / "f.md", quote.format("A Poet"))
    assert loader(tmp_path).load(front, "front", "prose", "Short").epigraph is None
    long_attr = write(tmp_path / "l.md", quote.format("X" * 70))
    assert loader(tmp_path).load(long_attr, "chapter", "prose", None).epigraph is None
    one = write(tmp_path / "o.md", "# T\n\n> Only one paragraph.\n\nBody.\n")
    assert loader(tmp_path).load(one, "chapter", "prose", "S").epigraph is None
    assert loader(tmp_path).load(front, "front", "prose", "Short").short == "Short"


def test_strict_loader_refuses_unfinished_markers_and_dashes(tmp_path: Path) -> None:
    path = write(tmp_path / "c.md", "# T\n\nFine.\n\nBroken [TODO fix] here.\n")
    with pytest.raises(ManuscriptError, match=r"c\.md:5: unfinished marker or dash '\[TODO fix\]'"):
        loader(tmp_path).load(path, "chapter", "prose", None)
    relaxed = loader(tmp_path, strict=False).load(path, "chapter", "prose", None)
    assert "[TODO fix]" in relaxed.body
    dash = write(tmp_path / "d.md", "# T\n\nA \u2014 dash.\n")
    with pytest.raises(ManuscriptError):
        loader(tmp_path).load(dash, "chapter", "prose", None)


def test_loader_requires_a_level_one_title(tmp_path: Path) -> None:
    path = write(tmp_path / "c.md", "No title here\n")
    with pytest.raises(ManuscriptError, match="level-1 title"):
        loader(tmp_path).load(path, "chapter", "prose", None)


def make_book(root: Path, extra: str = "") -> Path:
    write(root / "src" / "f.md", "# Foreword\n\nHello.\n")
    write(root / "src" / "a.md", "# Chapter 1: One\n\nOne.\n")
    write(root / "src" / "b.md", "# Chapter 2: Two\n\nTwo.\n")
    write(root / "src" / "n.md", "# Notes\n\nNotes.\n")
    write(root / "src" / "skip.md", "# Skipped\n\nx\n")
    config = (
        'source = "src"\ntitle = "T"\n'
        'front = ["f.md"]\nback = [{ file = "n.md", style = "references" }]\n'
        'not_in_book = ["skip.md"]\n'
        'parts = [{ title = "Part One", chapters = [{ file = "a.md", short = "Uno" }, "b.md"] }]\n'
        + extra
    )
    return write(root / "books" / "demo.toml", config)


def test_book_loader_numbers_chapters_only(tmp_path: Path) -> None:
    book = BookLoader(tmp_path).load(make_book(tmp_path))
    assert book.slug == "demo"
    assert [c.number for c in book.front] == [None]
    assert [(t, [(c.title, c.number, c.short) for c in cs]) for t, cs in book.parts] == [
        ("Part One", [("One", 1, "Uno"), ("Two", 2, "Two")])
    ]
    assert [(c.kind, c.style, c.number) for c in book.back] == [("back", "references", None)]


def test_book_loader_rejects_unlisted_sources(tmp_path: Path) -> None:
    config = make_book(tmp_path)
    write(tmp_path / "src" / "stray.md", "# Stray\n\nx\n")
    with pytest.raises(ManuscriptError, match=r"src/stray\.md is not listed in demo\.toml"):
        BookLoader(tmp_path).load(config)


def test_tex_text_escapes_and_keeps_line_breaks() -> None:
    tex = TexText()
    # A hard break is emitted as \\ + newline and the newline is then doubled, as in the original.
    assert tex.text("R&D 50%  \nnext") == "R\\&D 50\\%\\\\\\\\\nnext"
    assert tex.paragraphs("One.\n\n  Two & three.  ") == "One.\n\nTwo \\& three."


def test_chapter_tex_variants(tmp_path: Path) -> None:
    body = "Opening words here.\n"
    chapter = Chapter(tmp_path, "chapter", title="A & B", short="AB", body=body, number=1)
    numbered = ChapterTex().render(chapter)
    assert numbered.startswith("\\chapter{A \\& B}\n\\chapterheadmark{AB}\n")
    plain = ChapterTex().render(chapter, number_chapters=False)
    assert plain.startswith("\\chapter*{A \\& B}\n\\addcontentsline{toc}{chapter}{A \\& B}\n")
    front = Chapter(tmp_path, "front", title="Preface", short="Preface", body=body)
    assert (
        ChapterTex()
        .render(front)
        .startswith("\\chapter*{Preface}\n\\addcontentsline{toc}{chapter}{Preface}\n")
    )
    odd = Chapter(tmp_path, "front", title="Odd", short="O", body=body, number=4)
    assert "\\chapter*{Chapter~4: Odd}" in ChapterTex().render(odd)
    assert "{4\\hspace{1em}Odd}" in ChapterTex().render(odd)


def test_chapter_tex_includes_the_epigraph(tmp_path: Path) -> None:
    chapter = Chapter(
        tmp_path, "chapter", title="T", short="T", body="Body.\n", epigraph=("Quote.", "Source")
    )
    assert (
        "\\begin{chapterepigraph}{Source}\nQuote.\n\\end{chapterepigraph}\n"
        in ChapterTex().render(chapter)
    )
