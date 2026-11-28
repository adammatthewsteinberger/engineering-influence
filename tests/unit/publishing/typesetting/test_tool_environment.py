"""The build tools get an allow-listed environment, and LuaLaTeX never gets shell escape."""

import pytest

from engineering_influence.infrastructure.typesetting.tool_environment import ToolEnvironment

SECRETS = {
    "ANTHROPIC_API_KEY": "sk-secret",
    "EI_API_KEY": "key",
    "GITHUB_TOKEN": "tok",
    "AWS_SECRET_ACCESS_KEY": "aws",
}
NEEDED = {
    "PATH": "/usr/bin",
    "HOME": "/home/x",
    "LC_ALL": "C",
    "TEXMFHOME": "/tex",
    "TEXINPUTS": "/in",
}


def test_secrets_are_dropped_and_what_tex_needs_is_kept() -> None:
    built = ToolEnvironment({**SECRETS, **NEEDED}).build()
    assert built == {**NEEDED, "shell_escape": "f"}


def test_source_date_epoch_is_added_when_given() -> None:
    assert ToolEnvironment({"PATH": "/bin"}).build(42) == {
        "PATH": "/bin",
        "SOURCE_DATE_EPOCH": "42",
        "shell_escape": "f",
    }


def test_the_process_environment_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("TEXMFHOME", "/tex")
    built = ToolEnvironment().build()
    assert "ANTHROPIC_API_KEY" not in built and built["TEXMFHOME"] == "/tex"


def test_shell_escape_is_off_whatever_the_parent_says() -> None:
    assert ToolEnvironment({"shell_escape": "p"}).build()["shell_escape"] == "f"
    assert ToolEnvironment({}).build()["shell_escape"] == "f"
