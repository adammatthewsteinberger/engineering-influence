"""The script that turns the repository's Markdown into the documentation site's pages."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_docs_site.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_docs_site", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_docs_site"] = module
    spec.loader.exec_module(module)
    return module


SITE = load()
GITHUB = SITE.GITHUB
STAGED = {
    "README.md": "index.md",
    "docs/GETTING_STARTED.md": "getting-started.md",
    "docs/adr/0003-definition-of-1-0.md": "adr/0003-definition-of-1-0.md",
}
EXISTING = {
    "examples": "dir",
    "examples/README.md": "file",
    "src/engineering_influence/x.py": "file",
}


def kind(path: str) -> str | None:
    return EXISTING.get(path)


def rewrite(text: str, source: str = "docs/GETTING_STARTED.md", branch: str = "develop") -> str:
    return str(SITE.rewrite(text, source, STAGED, kind, branch))


# ------------------------------------------------------------------------------ addresses
@pytest.mark.parametrize(
    ("path", "address"),
    [
        ("README.md", "index.md"),
        ("CONTRIBUTING.md", "contributing.md"),
        ("CODE_OF_CONDUCT.md", "code-of-conduct.md"),
        ("docs/GETTING_STARTED.md", "getting-started.md"),
        ("docs/AGENTS_DRIVING.md", "agents-driving.md"),
        ("docs/adr/0009-branch-driven-publishing.md", "adr/0009-branch-driven-publishing.md"),
    ],
)
def test_each_page_has_a_clean_lower_case_address(path: str, address: str) -> None:
    assert SITE.staged_name(path) == address


def test_every_page_of_this_repository_is_found_and_none_is_given_twice() -> None:
    found = SITE.pages(ROOT)

    assert found["README.md"] == "index.md" and "docs/STYLE.md" in found
    assert len(set(found.values())) == len(found)
    assert all(address.endswith(".md") for address in found.values())
    assert {p.name for p in (ROOT / "docs" / "adr").glob("*.md")} <= {
        a.split("/")[-1] for a in found.values()
    }


def test_a_root_page_that_does_not_exist_is_simply_not_a_page(tmp_path: Path) -> None:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# x\n")

    assert SITE.pages(tmp_path) == {"README.md": "index.md"}


# ------------------------------------------------------------------------------ links
def test_a_link_to_another_page_becomes_a_link_between_the_pages() -> None:
    staged = {**STAGED, "docs/AGENTS_DRIVING.md": "agents-driving.md"}

    out = SITE.rewrite("[g](AGENTS_DRIVING.md)", "docs/GETTING_STARTED.md", staged, kind, "develop")

    assert out == "[g](agents-driving.md)"


def test_a_link_from_a_readme_into_docs_is_relative_to_the_site_root() -> None:
    assert rewrite("[s](docs/GETTING_STARTED.md)", source="README.md") == "[s](getting-started.md)"


def test_a_link_into_a_decision_record_keeps_its_folder_and_one_from_it_climbs_out() -> None:
    assert rewrite("[a](adr/0003-definition-of-1-0.md)") == "[a](adr/0003-definition-of-1-0.md)"
    assert rewrite("[g](../GETTING_STARTED.md)", source="docs/adr/0003-definition-of-1-0.md") == (
        "[g](../getting-started.md)"
    )


def test_an_absolute_github_link_to_a_page_becomes_a_link_between_pages() -> None:
    link = f"[g]({GITHUB}/blob/main/docs/GETTING_STARTED.md#install)"

    assert rewrite(link, source="README.md") == "[g](getting-started.md#install)"


def test_a_link_to_the_folder_of_decision_records_goes_to_their_index() -> None:
    assert rewrite(f"[a]({GITHUB}/tree/main/docs/adr)", source="README.md") == "[a](adr/index.md)"
    assert rewrite("[a](adr)", source="docs/GETTING_STARTED.md") == "[a](adr/index.md)"


def test_a_link_to_something_that_is_not_a_page_points_at_that_file_on_the_chosen_branch() -> None:
    assert (
        rewrite("[e](../examples/README.md#run)")
        == f"[e]({GITHUB}/blob/develop/examples/README.md#run)"
    )
    assert rewrite("[d](../examples)") == f"[d]({GITHUB}/tree/develop/examples)"
    assert (
        rewrite("[e](../examples/README.md)", branch="main")
        == f"[e]({GITHUB}/blob/main/examples/README.md)"
    )


def test_a_link_that_goes_nowhere_stops_the_build_and_names_the_page() -> None:
    with pytest.raises(SystemExit) as stopped:
        rewrite("[x](../nothing/here.md)")

    assert "docs/GETTING_STARTED.md: the link ../nothing/here.md goes nowhere" in str(stopped.value)


@pytest.mark.parametrize(
    "link",
    [
        "https://example.org/page",
        "mailto:someone@example.org",
        "#a-heading",
        f"{GITHUB}/releases",
        f"{GITHUB}/blob/main",
        "../../outside.md",
    ],
)
def test_a_link_that_is_not_to_a_repository_file_is_left_exactly_as_it_is(link: str) -> None:
    assert rewrite(f"[x]({link})") == f"[x]({link})"


def test_a_heading_anchor_is_written_the_way_the_site_writes_it() -> None:
    assert (
        rewrite("[c](GETTING_STARTED.md#check-it-ei-doctor---local)")
        == "[c](getting-started.md#check-it-ei-doctor-local)"
    )
    assert SITE.anchor("a--b---c-") == "a-b-c"
    assert SITE.anchor("-x") == "x"


def test_a_title_after_a_link_is_kept() -> None:
    assert rewrite('[g](GETTING_STARTED.md "the guide")') == '[g](getting-started.md "the guide")'


def test_code_is_never_rewritten_in_a_fence_or_in_a_span() -> None:
    text = (
        "```bash\n[a](../nothing/here.md)\n```\n"
        "and `[b](../nothing/here.md)` in a sentence, then [c](../examples)\n"
        "~~~\n[d](../nothing/here.md)\n~~~\n"
    )

    out = rewrite(text)

    assert "[a](../nothing/here.md)" in out and "`[b](../nothing/here.md)`" in out
    assert "[d](../nothing/here.md)" in out
    assert f"[c]({GITHUB}/tree/develop/examples)" in out


# ------------------------------------------------------------------------------ the decision records page
def test_the_decision_record_index_lists_each_record_with_its_status(tmp_path: Path) -> None:
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "0001-first.md").write_text("# ADR 0001: First\n\nStatus: accepted\n\nbody\n")
    (adr / "0002-second.md").write_text("# ADR 0002: Second\n\nno status here\n")
    (adr / "0003-empty.md").write_text("")

    text = SITE.adr_index(tmp_path)

    assert "| [ADR 0001: First](0001-first.md) | accepted |" in text
    assert "| [ADR 0002: Second](0002-second.md) |  |" in text
    assert "| [0003-empty](0003-empty.md) |  |" in text


# ------------------------------------------------------------------------------ the whole build
def small_repo(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs-site").mkdir()
    (tmp_path / "docs-site" / "site.css").write_text("a { color: red; }\n")
    (tmp_path / "examples").mkdir()
    (tmp_path / "README.md").write_text(
        "# Home\n\n[guide](docs/GETTING_STARTED.md) and [ex](examples)\n"
    )
    (tmp_path / "docs" / "GETTING_STARTED.md").write_text("# Start\n\n[home](../README.md)\n")
    (tmp_path / "docs" / "adr" / "0001-x.md").write_text("# ADR 0001: X\n\nStatus: accepted\n")
    (tmp_path / "llms.txt").write_text("# llms\n")
    return tmp_path


def test_the_build_writes_every_page_the_index_the_root_files_and_the_stylesheets(
    tmp_path: Path,
) -> None:
    repo, out = small_repo(tmp_path / "repo"), tmp_path / "out"

    written = SITE.build(repo, out, "develop")

    assert written == ["adr/0001-x.md", "adr/index.md", "getting-started.md", "index.md"]
    assert (
        (out / "index.md").read_text()
        == f"# Home\n\n[guide](getting-started.md) and [ex]({GITHUB}/tree/develop/examples)\n"
    )
    assert (out / "getting-started.md").read_text() == "# Start\n\n[home](index.md)\n"
    assert (out / "llms.txt").read_text() == "# llms\n" and not (out / "llms-full.txt").exists()
    assert (out / "stylesheets" / "site.css").read_text() == "a { color: red; }\n"
    assert (
        "Sitemap: https://adammatthewsteinberger.github.io/engineering-influence/sitemap.xml"
        in ((out / "robots.txt").read_text())
    )


def test_building_again_starts_from_nothing_so_a_deleted_page_does_not_linger(
    tmp_path: Path,
) -> None:
    repo, out = small_repo(tmp_path / "repo"), tmp_path / "out"
    SITE.build(repo, out, "develop")
    (repo / "docs" / "GETTING_STARTED.md").unlink()
    (repo / "README.md").write_text("# Home\n")

    SITE.build(repo, out, "develop")

    assert not (out / "getting-started.md").exists()


def test_the_stylesheet_comes_from_the_vibey_package_and_is_empty_when_it_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert ":root" in SITE.theme_stylesheet()

    monkeypatch.setitem(sys.modules, "vibey_gh", None)
    assert SITE.theme_stylesheet() == ""


def test_a_package_without_the_stylesheet_gives_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = ModuleType("vibey_gh")
    fake.__file__ = str(tmp_path / "vibey_gh" / "__init__.py")
    monkeypatch.setitem(sys.modules, "vibey_gh", fake)

    assert SITE.theme_stylesheet() == ""


def test_the_command_reports_what_it_wrote_and_warns_when_there_is_no_theme(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = small_repo(tmp_path / "repo")
    monkeypatch.setitem(sys.modules, "vibey_gh", None)

    assert SITE.main(["--root", str(repo), "--out", str(tmp_path / "out"), "--branch", "main"]) == 0

    captured = capsys.readouterr()
    assert "4 pages under" in captured.out
    assert "no Vibey stylesheet" in captured.err


def test_the_command_is_quiet_about_the_theme_when_it_has_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = small_repo(tmp_path / "repo")

    assert SITE.main(["--root", str(repo), "--out", str(tmp_path / "out")]) == 0

    assert capsys.readouterr().err == ""


# ------------------------------------------------------------------------------ this repository's own site
def navigation() -> list[str]:
    config = yaml.safe_load((ROOT / "properdocs.yml").read_text(encoding="utf-8"))
    found: list[str] = []

    def walk(items: object) -> None:
        if isinstance(items, str):
            found.append(items)
        elif isinstance(items, list):
            for item in items:
                walk(item)
        elif isinstance(items, dict):
            for value in items.values():
                walk(value)

    walk(config["nav"])
    return found


def test_the_navigation_lists_every_page_the_site_has_and_nothing_it_does_not(
    tmp_path: Path,
) -> None:
    written = set(SITE.build(ROOT, tmp_path / "site-src", "develop"))
    listed = navigation()

    assert len(listed) == len(set(listed)), "a page is in the navigation twice"
    assert set(listed) == written, (
        f"navigation differs from the pages: {sorted(set(listed) ^ written)}"
    )


def test_every_page_of_the_site_builds_with_no_link_to_nowhere(tmp_path: Path) -> None:
    out = tmp_path / "site-src"

    SITE.build(ROOT, out, "develop")

    assert (out / "index.md").read_text().startswith("# engineering-influence")
    assert "../" not in "".join((out / "getting-started.md").read_text().split("```"))


def test_the_site_config_names_what_the_scripts_and_the_workflow_expect() -> None:
    config = yaml.safe_load((ROOT / "properdocs.yml").read_text(encoding="utf-8"))

    assert config["docs_dir"] == ".site-src"
    assert config["site_url"] == "https://adammatthewsteinberger.github.io/engineering-influence/"
    assert config["repo_url"] == GITHUB
    assert config["extra_css"] == ["stylesheets/vibey.css", "stylesheets/site.css"]
    assert set(config["validation"].values()) == {"warn"}


def test_a_github_link_that_is_not_to_a_file_or_folder_of_the_repository_is_left_alone() -> None:
    link = f"{GITHUB}/issues/12/comments"

    assert rewrite(f"[i]({link})") == f"[i]({link})"


def test_the_build_writes_the_decision_record_index_and_lets_crawlers_in(tmp_path: Path) -> None:
    repo, out = small_repo(tmp_path / "repo"), tmp_path / "out"

    SITE.build(repo, out, "develop")

    assert "| [ADR 0001: X](0001-x.md) | accepted |" in (out / "adr" / "index.md").read_text()
    robots = (out / "robots.txt").read_text().splitlines()
    assert robots[:2] == ["User-agent: *", "Allow: /"]


def test_the_stylesheet_keeps_tables_readable_on_the_dark_theme() -> None:
    css = (ROOT / "docs-site" / "site.css").read_text(encoding="utf-8")

    # Every row, not only the even ones, takes the table's own text colour: Bootstrap's striped colour is black.
    assert "--bs-table-striped-color: var(--bs-table-color)" in css
    assert ".table.table-striped" in css
    # Cells wrap their prose, as the Vibey stylesheet would otherwise keep each on one line.
    assert "white-space: normal" in css
    # `break-word` as a word-break lets code break at any character, which squeezes a column to one letter wide.
    assert "word-break: break-word" not in css and "overflow-wrap: anywhere" not in css
    assert "overflow-x: auto" in css
