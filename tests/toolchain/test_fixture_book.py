"""Builds each fixture book with the real toolchain and compares it with its checked-in snapshot.

Run with ``uv run pytest -m toolchain``. It needs latexmk, LuaLaTeX, tex4ebook and epubcheck
(each fixture's release contract is strict), so CI runs it in its own job and a machine without
them skips it. Three books are built: a non-fiction book at the default 6x9 trim, a novel at 5.5x8.5
on cream paper (it follows different text rules and prints scene breaks), and a 5x8 pocket book with
no hardcover, which KDP does not print at that size. The expected snapshots were made
by that job on the pinned runner image; a different TeX Live release can legitimately change them.
To accept a deliberate change, run with ``EI_UPDATE_SNAPSHOT=1`` and commit the new files, or
download the ``fixture-snapshot`` artifact from the CI run (one ``<name>.json`` per book).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fixture_snapshot import FixtureSnapshot
from pypdf import PdfReader

pytestmark = pytest.mark.toolchain

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
# name -> (fixture directory, the book's slug)
BOOKS = {
    "fixture": ("fixture_book", "fixture"),
    "novel": ("fixture_novel", "novel"),
    "pocket": ("fixture_pocket", "pocket"),
}
STEPS = ["pdf", "hardcover", "covers", "epub"]
POCKET_STEPS = ["pdf", "covers", "epub"]  # no hardcover at 5x8
TOOLS = ("latexmk", "lualatex", "tex4ebook", "epubcheck")
BUILT: dict[str, Path] = {}


def build(name: str, factory: pytest.TempPathFactory) -> Path:
    """Publish a fixture once per run; every test of that book shares the result."""
    if name not in BUILT:
        missing = [tool for tool in TOOLS if shutil.which(tool) is None]
        if missing:
            pytest.skip(f"the TeX toolchain is not installed: {', '.join(missing)}")
        directory, slug = BOOKS[name]
        root = factory.mktemp(directory)
        shutil.copytree(FIXTURES / directory / "src", root / "src")
        shutil.copytree(FIXTURES / directory / "books", root / "books")
        command = [sys.executable, "-m", "engineering_influence", "book", "--root", str(root)]
        command += ["publish", slug, "--no-render", "--strict-release"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        BUILT[name] = root
    return BUILT[name]


@pytest.fixture(scope="module", params=sorted(BOOKS))
def built(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[str, Path]:
    return request.param, build(request.param, tmp_path_factory)


@pytest.fixture(scope="module")
def novel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build("novel", tmp_path_factory)


@pytest.fixture(scope="module")
def pocket(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build("pocket", tmp_path_factory)


def test_each_fixture_book_passes_the_whole_publication_pipeline(built: tuple[str, Path]) -> None:
    name, root = built
    slug = BOOKS[name][1]
    report = json.loads(
        (root / "build" / slug / "release" / "publication-report.json").read_text("utf-8")
    )
    assert report["status"] == "pass" and report.get("problems", []) == []
    expected = POCKET_STEPS if name == "pocket" else STEPS
    assert [step["name"] for step in report["steps"]] == expected


def test_the_build_matches_the_checked_in_snapshot(built: tuple[str, Path]) -> None:
    name, root = built
    directory, slug = BOOKS[name]
    expected = FIXTURES / directory / "expected" / "snapshot.json"
    actual = FixtureSnapshot().of(root, slug)
    text = json.dumps(actual, indent=2, sort_keys=True) + "\n"
    artifact_dir = os.environ.get("EI_SNAPSHOT_ARTIFACT_DIR")
    if artifact_dir:
        Path(artifact_dir).mkdir(parents=True, exist_ok=True)
        (Path(artifact_dir) / f"{name}.json").write_text(text, encoding="utf-8")
    if os.environ.get("EI_UPDATE_SNAPSHOT"):
        expected.parent.mkdir(parents=True, exist_ok=True)
        expected.write_text(text, encoding="utf-8")
    assert expected.exists(), f"no expected snapshot for {name}; run once with EI_UPDATE_SNAPSHOT=1"
    assert actual == json.loads(expected.read_text(encoding="utf-8"))


def test_the_novel_prints_its_scene_breaks_and_keeps_its_em_dashes(novel: Path) -> None:
    pdf = PdfReader(str(novel / "output" / "novel.pdf"))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    # Chapter one has two breaks and chapter two one; a rule that ends a chapter prints nothing.
    assert len(re.findall(r"^\* \* \*$", text, re.MULTILINE)) == 3
    assert "—" in text
    assert "Draft beer" in text
    with zipfile.ZipFile(novel / "output" / "novel.epub") as archive:
        pages = "".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xhtml")
        )
        sheet = archive.read("OEBPS/fine-ebook.css").decode("utf-8")
    assert pages.count("<p class='scenebreak'>") == 3
    assert "—" in pages
    assert "p.scenebreak + p.indent" in sheet


def pdf_facts(path: Path) -> tuple[int, tuple[float, float]]:
    reader = PdfReader(str(path))
    box = reader.pages[0].mediabox
    return len(reader.pages), (round(float(box.width), 1), round(float(box.height), 1))


def test_the_pocket_book_is_five_by_eight_with_no_hardcover_anywhere(pocket: Path) -> None:
    pages, size = pdf_facts(pocket / "output" / "pocket.pdf")
    assert size == (360.0, 576.0)
    covers = sorted(path.name for path in (pocket / "output" / "covers" / "pocket").iterdir())
    assert not [name for name in covers if "hardcover" in name]
    assert not (pocket / "output" / "pocket-hardcover.pdf").exists()
    # White paper: the wrap is bleed, two 5 in covers and a spine of 0.002252 in a page.
    wrap = pdf_facts(pocket / "output" / "covers" / "pocket" / "pocket-paperback-wrap.pdf")[1]
    assert wrap[0] == pytest.approx((0.25 + 10 + pages * 0.002252) * 72, abs=0.5)
    assert wrap[1] == pytest.approx((0.25 + 8) * 72, abs=0.5)


def test_the_novel_is_five_and_a_half_by_eight_and_a_half_and_its_spine_follows_cream_paper(
    novel: Path,
) -> None:
    pages, size = pdf_facts(novel / "output" / "novel.pdf")
    assert size == (396.0, 612.0)
    assert pdf_facts(novel / "output" / "novel-hardcover.pdf")[1] == (396.0, 612.0)
    wrap = pdf_facts(novel / "output" / "covers" / "novel" / "novel-paperback-wrap.pdf")[1]
    # Cream paper: 0.0025 in a page, so the spine is wider than white paper's of the same length.
    assert wrap[0] == pytest.approx((0.25 + 11 + pages * 0.0025) * 72, abs=0.5)
    assert wrap[0] > (0.25 + 11 + pages * 0.002252) * 72 + 0.2
