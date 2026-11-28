# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The macOS profile: no network, writes only in the server's directory, credentials kept out of reach."""

from pathlib import Path

from engineering_influence.infrastructure.tools.sandbox_exec_profile import SandboxExecProfile


def test_the_command_runs_under_sandbox_exec_with_the_profile_inline() -> None:
    wrapped = SandboxExecProfile("/usr/bin/sandbox-exec", Path("/Users/x")).wrap(
        ("/bin/server", "--stdio"), Path("/tmp/work")
    )
    assert wrapped[:3] == ("/usr/bin/sandbox-exec", "-p", wrapped[2])
    assert wrapped[3:] == ("/bin/server", "--stdio")


def test_the_profile_denies_by_default_and_the_network_and_allows_reads() -> None:
    profile = SandboxExecProfile("/usr/bin/sandbox-exec", Path("/Users/x")).profile(
        Path("/tmp/work")
    )
    assert profile.startswith("(version 1)\n(deny default)\n")
    assert "(allow file-read*)" in profile
    assert profile.rstrip().endswith("(deny network*)")


def test_writes_are_allowed_only_under_the_resolved_working_directory(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    profile = SandboxExecProfile("/usr/bin/sandbox-exec", Path("/Users/x")).profile(work)
    assert f'(allow file-write* (subpath "{work.resolve()}"))' in profile


def test_credential_directories_are_denied_after_reads_are_allowed() -> None:
    profile = SandboxExecProfile("/usr/bin/sandbox-exec", Path("/Users/x")).profile(
        Path("/tmp/work")
    )
    allowed = profile.index("(allow file-read*)")
    for name in SandboxExecProfile.SECRET_DIRECTORIES:
        denial = f'(deny file-read* (subpath "{Path("/Users/x", name)}"))'
        assert denial in profile
        assert profile.index(denial) > allowed


def test_a_quote_or_backslash_in_a_path_cannot_end_the_quoted_string() -> None:
    odd = Path('/tmp/a"b\\c')
    profile = SandboxExecProfile("/usr/bin/sandbox-exec", Path("/Users/x")).profile(odd)
    assert 'a\\"b\\\\c"))' in profile
