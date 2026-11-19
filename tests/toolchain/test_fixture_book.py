"""Builds the fixture book with the real toolchain and compares it with the checked-in snapshot.

Run with ``uv run pytest -m toolchain``. It needs latexmk, LuaLaTeX, tex4ebook and epubcheck
(the fixture's release contract is strict), so CI runs it in its own job and a machine without
them skips it. The expected snapshot was made
by that job on the pinned runner image; a different TeX Live release can legitimately change it.
To accept a deliberate change, run with ``EI_UPDATE_SNAPSHOT=1`` and commit the new file.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fixture_snapshot import FixtureSnapshot

pytestmark = pytest.mark.toolchain

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "fixture_book"
EXPECTED = FIXTURE / "expected" / "snapshot.json"
TOOLS = ("latexmk", "lualatex", "tex4ebook", "epubcheck")


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"the TeX toolchain is not installed: {', '.join(missing)}")
    root = tmp_path_factory.mktemp("fixture_book")
    shutil.copytree(FIXTURE / "src", root / "src")
    shutil.copytree(FIXTURE / "books", root / "books")
    command = [sys.executable, "-m", "engineering_influence", "book", "--root", str(root)]
    command += ["publish", "fixture", "--no-render", "--strict-release"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return root


def test_the_fixture_book_passes_the_whole_publication_pipeline(built: Path) -> None:
    report = json.loads(
        (built / "build" / "fixture" / "release" / "publication-report.json").read_text("utf-8")
    )
    assert report["status"] == "pass" and report.get("problems", []) == []
    assert [step["name"] for step in report["steps"]] == ["pdf", "hardcover", "covers", "epub"]


def test_the_build_matches_the_checked_in_snapshot(built: Path) -> None:
    actual = FixtureSnapshot().of(built, "fixture")
    text = json.dumps(actual, indent=2, sort_keys=True) + "\n"
    artifact_dir = os.environ.get("EI_SNAPSHOT_ARTIFACT_DIR")
    if artifact_dir:
        Path(artifact_dir).mkdir(parents=True, exist_ok=True)
        (Path(artifact_dir) / "snapshot.json").write_text(text, encoding="utf-8")
    if os.environ.get("EI_UPDATE_SNAPSHOT"):
        EXPECTED.parent.mkdir(parents=True, exist_ok=True)
        EXPECTED.write_text(text, encoding="utf-8")
    assert EXPECTED.exists(), "no expected snapshot; run once with EI_UPDATE_SNAPSHOT=1"
    assert actual == json.loads(EXPECTED.read_text(encoding="utf-8"))
