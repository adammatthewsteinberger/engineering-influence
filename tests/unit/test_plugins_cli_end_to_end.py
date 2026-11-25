# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""``ei plugins`` over real files: installing locks skills and records a hash, and starts and grants nothing."""

import hashlib
import stat
from pathlib import Path

import pytest

from engineering_influence.runtime.cli_runtime import CliRuntime


class Project:
    def __init__(self, root: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.root = root
        self.plugin_lock = root / "ei-plugins.lock.toml"
        self.skill_lock = root / "ei-skills.lock.toml"
        self.tool_lock = root / "ei-tools.lock.toml"
        self.marker = root / "server-was-started"
        self.server = root / "server.sh"
        self.server.write_text(f'#!/bin/sh\ntouch "{self.marker}"\n', encoding="utf-8")
        self.server.chmod(self.server.stat().st_mode | stat.S_IXUSR)
        self.bundle = root / "elsewhere" / "research_pack.toml"
        self.bundle.parent.mkdir()
        self.text = (
            'name = "research_pack"\nversion = 1\ndescription = "Sources and style."\n\n'
            '[[server]]\nname = "files"\n'
            f'command = ["{self.server}"]\n\n'
            '[[server]]\nname = "docs"\nurl = "https://mcp.example.com/v1/mcp"\n'
            'bearer_env = "DOCS_TOKEN"\n\n'
            '[[skill]]\nname = "plain_style"\nversion = 2\ndescription = "Short sentences."\n\n'
            '[skill.parts]\noutline = "Prefer short chapters."\nresearch = "Say where you read it."\n'
        )
        self.bundle.write_text(self.text, encoding="utf-8")
        self.cli = CliRuntime().build()
        self.capsys = capsys

    def plugins(self, command: str, *rest: str) -> tuple[int, str, str]:
        locks = () if command == "show" else ("--lock", str(self.plugin_lock))
        skills = (
            ("--skill-lock", str(self.skill_lock)) if command in {"add", "verify", "remove"} else ()
        )
        status = self.cli.run(["plugins", command, *locks, *skills, *rest])
        captured = self.capsys.readouterr()
        return status, captured.out, captured.err

    def skills(self, command: str, *rest: str) -> tuple[int, str, str]:
        status = self.cli.run(["skills", command, "--lock", str(self.skill_lock), *rest])
        captured = self.capsys.readouterr()
        return status, captured.out, captured.err


@pytest.fixture
def project(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Project:
    return Project(tmp_path, capsys)


def test_installing_locks_the_skills_records_the_hash_and_prints_the_commands_for_the_servers(
    project: Project,
) -> None:
    status, out, _ = project.plugins("add", str(project.bundle))
    assert status == 0 and "installed research_pack@1" in out
    digest = hashlib.sha256(project.text.encode()).hexdigest()
    assert (project.root / "plugins" / "research_pack.toml").read_text(
        encoding="utf-8"
    ) == project.text
    lock = project.plugin_lock.read_text(encoding="utf-8")
    assert (
        f'name = "research_pack"\nversion = 1\nsha256 = "{digest}"\nservers = ["docs", "files"]'
        in lock
    )
    assert '[plugin.skills]\nplain_style = "' in lock
    assert (project.root / "skills" / "plain_style.toml").is_file()
    assert "stages = []" in project.skill_lock.read_text(encoding="utf-8")
    assert "ei tools add --bearer-env DOCS_TOKEN --url https://mcp.example.com/v1/mcp docs" in out
    assert f"ei tools add files -- {project.server}" in out


def test_installing_starts_no_server_creates_no_tool_lock_and_grants_nothing(
    project: Project,
) -> None:
    assert project.plugins("add", str(project.bundle))[0] == 0
    assert not project.marker.exists()
    assert not project.tool_lock.exists()
    assert "stages = []" in project.skill_lock.read_text(encoding="utf-8")
    assert project.skills("list")[1].endswith("enabled for no stage\n")


def test_showing_changes_nothing_at_all(project: Project) -> None:
    status, out, _ = project.plugins("show", str(project.bundle))
    assert status == 0 and "research_pack@1" in out and "ei tools add" in out
    assert sorted(path.name for path in project.root.iterdir()) == [
        "elsewhere",
        "server.sh",
    ]


def test_the_skills_it_installed_are_ordinary_skills_a_person_enables_and_verifies(
    project: Project,
) -> None:
    project.plugins("add", str(project.bundle))
    assert project.skills("verify")[0] == 0
    assert project.skills("enable", "plain_style", "outline")[0] == 0
    assert project.plugins("verify")[0] == 0
    assert 'stages = ["outline"]' in project.skill_lock.read_text(encoding="utf-8")


def test_a_plugin_cannot_be_installed_twice_or_over_skills_that_are_locked(
    project: Project,
) -> None:
    project.plugins("add", str(project.bundle))
    status, _, err = project.plugins("add", str(project.bundle))
    assert status == 2 and "already installed" in err
    project.plugins("remove", "research_pack")
    other = project.root / "x" / "plain_style.toml"
    other.parent.mkdir()
    other.write_text(
        'name = "plain_style"\nversion = 1\n[parts]\nbrief = "mine"\n', encoding="utf-8"
    )
    assert project.skills("add", str(other))[0] == 0
    status, _, err = project.plugins("add", str(project.bundle))
    assert status == 2 and "already locked: plain_style" in err
    assert not (project.root / "plugins" / "research_pack.toml").exists()


def test_a_bundle_changed_after_installing_or_a_skill_locked_again_fails_verify(
    project: Project,
) -> None:
    project.plugins("add", str(project.bundle))
    copy = project.root / "plugins" / "research_pack.toml"
    copy.write_text(project.text.replace("Sources", "sources"), encoding="utf-8")
    status, out, _ = project.plugins("verify")
    assert status == 1 and "has changed since it was installed" in out
    copy.write_text(project.text, encoding="utf-8")
    assert project.plugins("verify")[0] == 0
    project.skills("remove", "plain_style")
    status, out, _ = project.plugins("verify")
    assert status == 1 and "its skill 'plain_style' is no longer locked" in out


def test_removing_takes_out_the_plugin_and_its_unchanged_skills_and_not_a_changed_one(
    project: Project,
) -> None:
    project.plugins("add", str(project.bundle))
    status, out, _ = project.plugins("remove", "research_pack")
    assert status == 0 and "skills removed with it: plain_style" in out
    assert not (project.root / "skills" / "plain_style.toml").exists()
    assert not (project.root / "plugins" / "research_pack.toml").exists()
    assert project.plugins("list")[1] == f"{project.plugin_lock} locks no plugins\n"
    assert not project.marker.exists()


def test_a_skill_locked_again_since_is_left_when_the_plugin_is_removed(project: Project) -> None:
    project.plugins("add", str(project.bundle))
    project.skills("remove", "plain_style")
    mine = project.root / "mine" / "plain_style.toml"
    mine.parent.mkdir()
    mine.write_text(
        'name = "plain_style"\nversion = 1\n[parts]\nbrief = "mine"\n', encoding="utf-8"
    )
    project.skills("add", str(mine))
    status, out, _ = project.plugins("remove", "research_pack")
    assert status == 0 and "left in place because they were locked again" in out
    assert "plain_style" in project.skill_lock.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "extra",
    ['grants = ["research"]', 'stages = ["outline"]', 'tools = ["shell"]'],
)
def test_a_bundle_has_no_way_to_grant_a_tool_or_enable_a_skill(
    project: Project, extra: str
) -> None:
    project.bundle.write_text(extra + "\n" + project.text, encoding="utf-8")
    status, _, err = project.plugins("add", str(project.bundle))
    assert status == 2 and "unknown keys" in err
    assert not project.plugin_lock.exists() and not project.skill_lock.exists()


def test_a_server_a_bundle_describes_that_the_lock_would_refuse_is_refused_up_front(
    project: Project,
) -> None:
    project.bundle.write_text(
        project.text.replace(
            f'command = ["{project.server}"]', 'command = ["/usr/bin/npx", "server"]'
        ),
        encoding="utf-8",
    )
    status, _, err = project.plugins("add", str(project.bundle))
    assert status == 2 and "fetches code that cannot be hashed" in err
    assert not project.skill_lock.exists() and not (project.root / "plugins").exists()
