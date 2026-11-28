# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The macOS profile: no network, writes only in the server's directory, and no reads of the home directory except
the server's own interpreter and files."""

from pathlib import Path

from engineering_influence.infrastructure.tools.sandbox_allowance import SandboxAllowance
from engineering_influence.infrastructure.tools.sandbox_exec_profile import SandboxExecProfile

HOME = Path("/Users/x")


def profile_for(workdir: Path, allowed: tuple[Path, ...] = ()) -> str:
    return SandboxExecProfile("/usr/bin/sandbox-exec", HOME, SandboxAllowance()).profile(
        workdir, allowed
    )


def test_the_command_runs_under_sandbox_exec_with_the_profile_inline(tmp_path: Path) -> None:
    wrapped = SandboxExecProfile("/usr/bin/sandbox-exec", HOME, SandboxAllowance()).wrap(
        ("/bin/server", "--stdio"), tmp_path
    )
    assert wrapped[:2] == ("/usr/bin/sandbox-exec", "-p")
    assert wrapped[3:] == ("/bin/server", "--stdio")


def test_the_profile_denies_by_default_and_the_network_and_allows_reads(tmp_path: Path) -> None:
    profile = profile_for(tmp_path)
    assert profile.startswith("(version 1)\n(deny default)\n")
    assert "(allow file-read*)" in profile
    assert profile.rstrip().endswith("(deny network*)")


def test_process_rules_are_fork_and_exec_only_not_every_process_operation(tmp_path: Path) -> None:
    profile = profile_for(tmp_path)
    assert "(allow process*)" not in profile
    assert "(allow process-fork)" in profile and "(allow process-exec)" in profile


def test_the_whole_home_directory_is_denied_after_reads_are_allowed(tmp_path: Path) -> None:
    profile = profile_for(tmp_path)
    denial = f'(deny file-read* (subpath "{HOME}"))'
    assert denial in profile
    assert profile.index(denial) > profile.index("(allow file-read*)\n")


def test_an_allowance_is_re_opened_after_the_home_denial(tmp_path: Path) -> None:
    venv = HOME / "proj" / ".venv"
    profile = profile_for(tmp_path, (venv,))
    assert profile.index(f'(allow file-read* (subpath "{venv}"))') > profile.index(
        f'(deny file-read* (subpath "{HOME}"))'
    )


def test_writes_are_allowed_only_under_the_resolved_working_directory(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    profile = profile_for(work)
    assert f'(allow file-write* (subpath "{work.resolve()}"))' in profile


def test_a_quote_or_backslash_in_a_path_cannot_end_the_quoted_string() -> None:
    odd = Path('/tmp/a"b\\c')
    profile = profile_for(odd)
    assert 'a\\"b\\\\c"))' in profile
