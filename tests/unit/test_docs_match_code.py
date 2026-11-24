# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The documents name every command and every environment variable the code has, and nothing it has not."""

import json
import re
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
