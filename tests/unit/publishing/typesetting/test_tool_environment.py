"""The build tools get an allow-listed environment, and LuaLaTeX never gets shell escape."""

from pathlib import Path

import pytest

from engineering_influence.publishing.typesetting.latex_compiler import LatexCompiler
from engineering_influence.publishing.typesetting.tool_environment import ToolEnvironment

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
    assert built == NEEDED


def test_source_date_epoch_is_added_when_given() -> None:
    assert ToolEnvironment({"PATH": "/bin"}).build(42) == {
        "PATH": "/bin",
        "SOURCE_DATE_EPOCH": "42",
    }


def test_the_process_environment_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("TEXMFHOME", "/tex")
    built = ToolEnvironment().build()
    assert "ANTHROPIC_API_KEY" not in built and built["TEXMFHOME"] == "/tex"


def test_latexmk_runs_without_shell_escape_and_without_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: dict[str, object] = {}

    class Result:
        returncode = 0
        stdout = "ok"

    def fake_run(command: list[str], **kwargs: object) -> Result:
        seen["command"], seen["env"] = command, kwargs["env"]
        return Result()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setattr("subprocess.run", fake_run)
    assert LatexCompiler().compile(tmp_path, "book.tex", 7) == (0, "ok")
    assert "-no-shell-escape" in seen["command"]  # type: ignore[operator]
    env = seen["env"]
    assert isinstance(env, dict) and "ANTHROPIC_API_KEY" not in env
    assert env["SOURCE_DATE_EPOCH"] == "7"
