# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The documents name every command and every environment variable the code has, and nothing it has not."""

import itertools
import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_ONLY = {"EI_API_PORT", "EI_SEARXNG_PORT"}  # read by Docker Compose, never by the program


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def variables_in_code() -> set[str]:
    found: set[str] = set()
    for folder in ("src", "packages"):
        for path in (ROOT / folder).rglob("*.py"):
            found |= set(
                re.findall(r"""["'](EI_[A-Z0-9_]+)["']""", path.read_text(encoding="utf-8"))
            )
    return found


def variables_in_the_index() -> set[str]:
    text = read("docs/CONFIGURATION.md")
    section = text.split("### Every variable, and where it is described", 1)[1].split("\n```", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("| `EI_")]
    return {name for row in rows for name in re.findall(r"`(EI_[A-Z0-9_]+)`", row.split("|")[1])}


def test_the_index_has_a_row_for_every_variable_the_code_reads() -> None:
    missing = variables_in_code() - variables_in_the_index()

    assert not missing, f"add these to the index in docs/CONFIGURATION.md: {sorted(missing)}"


def test_the_index_names_nothing_that_no_code_or_compose_file_uses() -> None:
    stale = variables_in_the_index() - variables_in_code() - COMPOSE_ONLY

    assert not stale, f"these are in the index but nothing reads them: {sorted(stale)}"


def test_the_compose_only_variables_really_are_read_by_a_compose_file() -> None:
    compose = read("examples/docker-compose.yml") + read("examples/searxng/docker-compose.yml")

    for name in COMPOSE_ONLY:
        assert name in compose, name
        assert name in variables_in_the_index()


def commands() -> list[str]:
    tree = json.loads(read("tests/contracts/snapshots/cli_command_tree.json"))
    names: list[str] = []
    for top, spec in tree["commands"].items():
        names.append(top)
        names += [f"{top} {sub}" for sub in spec.get("commands", {})]
    return names


@pytest.mark.parametrize("command", commands())
def test_every_command_the_cli_has_is_in_the_interactions_reference(command: str) -> None:
    text = read("docs/INTERACTIONS.md")
    top, _, sub = command.partition(" ")
    # A command appears in the synopsis or the table, possibly grouped as `run status|resume|cancel`.
    grouped = rf"ei {top} (?:[\w\[\]\-\s.|]*?)\b{sub}\b" if sub else rf"\bei {top}\b"

    assert re.search(grouped, text), f"docs/INTERACTIONS.md never mentions `ei {command}`"


def test_every_tool_the_mcp_server_offers_is_in_the_interactions_reference() -> None:
    tools = json.loads(read("tests/contracts/snapshots/mcp_tools.json"))
    names = [t["name"] for t in tools] if isinstance(tools, list) else list(tools)
    text = read("docs/INTERACTIONS.md")

    for name in names:
        assert f"`{name}`" in text, f"docs/INTERACTIONS.md never lists the MCP tool {name}"


# ------------------------------------------------------------------------------ the page pattern (docs/STYLE.md)
INSTALL = "curl -fsSL https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence/main/install.sh | sh"
BLOB = "https://github.com/adammatthewsteinberger/engineering-influence/"
LAYERED = (
    "README.md",
    "docs/GETTING_STARTED.md",
    "docs/AGENTS_DRIVING.md",
    "docs/BOOKS_AND_KDP.md",
    "examples/README.md",
    "docs/ARCHITECTURE.md",
    "docs/COMPATIBILITY.md",
    "docs/CONFIGURATION.md",
    "docs/EVALUATION.md",
    "docs/INTERACTIONS.md",
    "docs/LIVE_SMOKE_TEST.md",
    "docs/LOCAL_MODEL.md",
    "docs/MODEL_CALLS.md",
    "docs/MODEL_CATALOG.md",
    "docs/MODEL_PROFILES.md",
    "docs/NOVELS.md",
    "docs/PROMPTS.md",
    "docs/RESEARCH.md",
    "docs/DOCUMENTATION_SITE.md",
    "CONTRIBUTING.md",
    "docs/PLUGINS.md",
    "docs/RELEASING.md",
    "docs/SKILLS.md",
    "docs/TESTING.md",
    "docs/TOOL_LOCK.md",
    "docs/TROUBLESHOOTING.md",
    "docs/WORKER_IMAGE.md",
)
PLAIN = (
    "AGENTS.md",
    "docs/DEPLOYMENT.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "llms.txt",
    "llms-full.txt",
    "docs/STYLE.md",
    "docs/AUDIOBOOKS.md",
    "docs/SCREENPLAYS.md",
    "docs/WEBHOOKS.md",
    "docs/THREAT_MODEL.md",
    "packages/engineering-influence-sdk/README.md",
    "examples/claude-code/engineering-influence/SKILL.md",
)
# Pages still to be rewritten to the pattern. Empty: every teaching page now follows it.
PENDING: tuple[str, ...] = ()
SPEAKERS = ("Daniel", "Professor Feynman")


def scenes(text: str) -> list[list[str]]:
    """Each scene as the list of who speaks, in order: a run of block-quote lines that name a speaker."""
    found: list[list[str]] = []
    current: list[str] = []
    for line in [*text.splitlines(), ""]:
        if line.startswith(">"):
            spoken = re.match(r">\s*\*\*(Daniel|Professor Feynman):\*\*", line)
            if spoken:
                current.append(spoken.group(1))
        elif current:
            found.append(current)
            current = []
    return found


def test_every_page_is_either_layered_plain_or_still_to_be_rewritten() -> None:
    pages = {str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md")}
    pages |= {str(p.relative_to(ROOT)) for p in ROOT.glob("*.md")}
    listed = set(LAYERED) | set(PLAIN) | set(PENDING)

    assert pages <= listed, f"say how these pages are written: {sorted(pages - listed)}"
    assert not set(LAYERED) & set(PLAIN) and not set(LAYERED) & set(PENDING)
    for page in listed:
        assert (ROOT / page).is_file(), page


@pytest.mark.parametrize("page", LAYERED)
def test_a_layered_page_opens_with_the_bottom_line_before_anything_else(page: str) -> None:
    lines = [line for line in read(page).splitlines() if line.strip()]

    assert lines[0].startswith("# ")
    opening = "\n".join(lines[1:6])
    assert "**BLUF:**" in opening, f"{page} must give the bottom line directly under its title"
    assert opening.index("**BLUF:**") < (opening + "\n## ").index("\n## ")


@pytest.mark.parametrize("page", LAYERED)
def test_a_layered_page_has_a_scene_that_follows_the_rules(page: str) -> None:
    found = scenes(read(page))

    assert found, f"{page} has no scene between the Professor and Daniel"
    for speakers in found:
        assert 6 <= len(speakers) <= 14, f"a scene in {page} has {len(speakers)} lines of dialogue"
        assert speakers[0] == "Daniel", f"a scene in {page} must open on Daniel's problem"
        assert speakers[-1] == "Daniel", f"a scene in {page} must end with Daniel testing the idea"
        assert set(speakers) == set(SPEAKERS)
        assert all(a != b for a, b in itertools.pairwise(speakers)), page


@pytest.mark.parametrize("page", LAYERED)
def test_the_scene_comes_after_the_bottom_line_and_before_the_reference(page: str) -> None:
    text = read(page)

    assert text.index("**BLUF:**") < text.index("**Daniel:**")
    assert "|---" in text[text.index("**Daniel:**") :], (
        f"{page} has no reference table after its scene"
    )


@pytest.mark.parametrize("page", [*PLAIN, *PENDING])
def test_a_plain_page_has_no_scene(page: str) -> None:
    assert scenes(read(page)) == [], f"{page} is a plain page and must not carry a scene"


def test_the_professor_is_said_to_be_fictional_where_the_pattern_is_defined() -> None:
    assert "fictional teacher" in read("docs/STYLE.md")
    assert "Nothing he says here is a quotation" in read("docs/STYLE.md")


# ------------------------------------------------------------------------------ links
def markdown_files() -> list[Path]:
    found = [*ROOT.glob("*.md"), ROOT / "llms.txt", ROOT / "llms-full.txt"]
    for folder in ("docs", "examples", "packages", "changelog.d"):
        found += [p for p in (ROOT / folder).rglob("*.md") if ".venv" not in p.parts]
    return sorted(found)


def anchors(path: Path) -> set[str]:
    """The anchors GitHub gives a file's headings: lower case, punctuation dropped, spaces to hyphens, repeats numbered."""
    seen: dict[str, int] = {}
    found: set[str] = set()
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
        heading = re.match(r"#{1,6}\s+(.*)", line)
        if fenced or not heading:
            continue
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.group(1)).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", text).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        found.add(slug if count == 0 else f"{slug}-{count}")
    return found


def links(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return re.findall(r"\]\(([^)\s]+)\)", re.sub(r"`[^`\n]*`", "", text))


def target(source: Path, link: str) -> tuple[Path, str] | None:
    """The local file and anchor a link points at, or None when it leaves this repository."""
    address, _, anchor = link.partition("#")
    if address.startswith(BLOB):
        kind, _, rest = address.removeprefix(BLOB).partition("/")
        if kind not in ("blob", "tree"):
            return None
        return ROOT / rest.partition("/")[2], anchor
    if re.match(r"[a-z][a-z0-9+.-]*:", address):
        return None
    # A changelog fragment is folded into CHANGELOG.md at the root, so its links are read from there.
    base = (
        ROOT
        if source.parent.name == "changelog.d" and source.name != "README.md"
        else source.parent
    )
    return (source if not address else (base / address).resolve()), anchor


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_every_link_in_every_document_goes_somewhere(path: Path) -> None:
    broken: list[str] = []
    for link in links(path):
        found = target(path, link)
        if found is None:
            continue
        file, anchor = found
        if not file.exists():
            broken.append(f"{link}: no such file")
        elif anchor and file.suffix == ".md" and anchor not in anchors(file):
            broken.append(f"{link}: no such heading")

    assert not broken, f"{path.relative_to(ROOT)} has links that go nowhere: {broken}"


def test_the_link_checker_can_tell_a_good_link_from_a_bad_one(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "# Top\n\n## A `code` heading!\n\n## Twice\n\n## Twice\n\n```\n## not a heading\n```\n"
    )

    assert anchors(page) == {"top", "a-code-heading", "twice", "twice-1"}
    assert target(page, "other.md#x") == (tmp_path / "other.md", "x")
    assert target(page, "#twice") == (page, "twice")
    assert target(page, "https://example.org/page") is None
    assert target(page, "mailto:someone@example.org") is None
    assert target(page, f"{BLOB}blob/main/docs/STYLE.md#the-three-layers") == (
        ROOT / "docs" / "STYLE.md",
        "the-three-layers",
    )
    assert target(page, f"{BLOB}tree/main/examples") == (ROOT / "examples", "")
    assert target(page, f"{BLOB}releases") is None
    assert links(page) == []


# ------------------------------------------------------------------------------ the install command and the index
@pytest.mark.parametrize(
    "page",
    [
        "README.md",
        "docs/GETTING_STARTED.md",
        "docs/AGENTS_DRIVING.md",
        "llms.txt",
        "llms-full.txt",
        "examples/claude-code/engineering-influence/SKILL.md",
        "install.sh",
    ],
)
def test_the_install_command_is_the_same_one_everywhere(page: str) -> None:
    assert INSTALL in read(page), f"{page} must show the install command exactly"


def test_the_bottom_line_of_the_front_page_has_the_install_command_and_the_command_that_writes_a_book() -> (
    None
):
    top = read("README.md").split("\n## ", 1)[0]

    assert INSTALL in top and "ei book create --kind nonfiction" in top
    assert top.index("**BLUF:**") < top.index(INSTALL) < top.index("ei book create")


@pytest.mark.parametrize("index", ["llms.txt", "README.md"])
def test_the_indexes_list_every_document(index: str) -> None:
    text = read(index)
    missing = [
        p.name for p in sorted((ROOT / "docs").glob("*.md")) if f"/docs/{p.name}" not in text
    ]

    assert not missing, f"{index} does not link these documents: {missing}"


def test_the_exit_codes_an_agent_is_told_are_the_ones_the_command_returns() -> None:
    source = read("src/engineering_influence/interactions/cli/book_cli.py")

    assert {int(code) for code in re.findall(r"return ([0-9])\b", source)} >= {0, 1, 2, 3}
    for page in (
        "llms-full.txt",
        "docs/AGENTS_DRIVING.md",
        "examples/claude-code/engineering-influence/SKILL.md",
    ):
        text = read(page)
        assert "--resume --approve-spend" in text, page
        for code in ("0", "1", "2", "3"):
            assert re.search(rf"(^|[|`\s]){code}(`|\s|\|)", text, re.MULTILINE), (page, code)


def test_the_prompts_page_lists_every_template_that_ships_with_its_version() -> None:
    folder = ROOT / "src/engineering_influence/infrastructure/prompt_library/templates"
    text = read("docs/PROMPTS.md")
    shipped = sorted(folder.glob("*.toml"))

    for template in shipped:
        version = re.search(
            r"^version = (\d+)$", template.read_text(encoding="utf-8"), re.MULTILINE
        )
        assert version, template.name
        assert f"| `{template.stem}` | {version.group(1)} |" in text, (
            f"docs/PROMPTS.md must list {template.stem} at version {version.group(1)}"
        )
    listed = re.findall(r"^\| `([a-z_]+)` \| \d+ \|", text, re.MULTILINE)
    assert sorted(listed) == [template.stem for template in shipped]


def test_the_compatibility_page_says_how_many_contracts_it_lists() -> None:
    text = read("docs/COMPATIBILITY.md")
    table = text.split("## The contracts", 1)[1].split("\n## ", 1)[0]
    rows = [
        row
        for row in table.splitlines()
        if row.startswith("| ") and not row.startswith("| Contract")
    ]
    words = [
        "Zero",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
    ]

    assert f"**BLUF:** {words[len(rows)]} public contracts are frozen" in text


def flags() -> list[tuple[str, str]]:
    tree = json.loads(read("tests/contracts/snapshots/cli_command_tree.json"))
    found: list[tuple[str, str]] = []

    def walk(name: str, spec: dict[str, object]) -> None:
        for argument in spec.get("arguments", []):  # type: ignore[attr-defined]
            found.extend((name, flag) for flag in argument["flags"])
        for sub, inner in spec.get("commands", {}).items():  # type: ignore[attr-defined]
            walk(f"{name} {sub}".strip(), inner)

    walk("", tree)
    return found


@pytest.mark.parametrize(("command", "flag"), flags(), ids=lambda v: str(v))
def test_every_flag_of_every_command_is_in_the_interactions_reference(
    command: str, flag: str
) -> None:
    assert flag in read("docs/INTERACTIONS.md"), (
        f"docs/INTERACTIONS.md never shows {flag} of `ei {command}`"
    )


def test_the_brief_table_has_a_row_for_every_field_the_contract_accepts() -> None:
    schema = json.loads(read("tests/contracts/snapshots/brief_v1_schema.json"))
    text = read("docs/INTERACTIONS.md")
    table = text.split("A **book run** starts from a **brief**", 1)[1].split("\n\n", 2)[1]

    for field in schema["properties"]:
        assert f"`{field}`" in table, (
            f"the brief table in docs/INTERACTIONS.md has no row for {field}"
        )
    assert (
        schema["additionalProperties"] is False and "Any key not in this table is refused" in text
    )


def test_the_evaluation_page_names_every_dimension_of_the_rubric() -> None:
    rubric = tomllib.loads(read("evaluation/rubric.toml"))
    names = [dimension["name"] for dimension in rubric["dimension"]]
    text = read("docs/EVALUATION.md")

    assert names
    for name in names:
        assert f"`{name}`" in text, f"docs/EVALUATION.md does not name the rubric dimension {name}"
