# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ServerEnvironment: a server gets a short list, a throwaway home, and only what the lock names."""

import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.server_environment import ServerEnvironment

PARENT = {
    "PATH": "/usr/bin:/bin",
    "LANG": "en_US.UTF-8",
    "TZ": "UTC",
    "SYSTEMROOT": "C:\\Windows",
    "LC_ALL": "C",
    "LC_TIME": "en_GB",
    "HOME": "/home/me",
    "TMPDIR": "/tmp/me",
    "ANTHROPIC_API_KEY": "sk-secret",
    "AWS_SECRET_ACCESS_KEY": "aws-secret",
    "GITHUB_TOKEN": "ghp-secret",
    "FILES_ROOT": "/data",
    "TOKEN": "tok",
}


def build(*names: str, workdir: str = "/work/dir") -> dict[str, str]:
    return ServerEnvironment(PARENT).build(names, Path(workdir))


def test_only_the_allow_list_gets_through_and_no_secret_does() -> None:
    env = build()
    assert env["PATH"] == "/usr/bin:/bin" and env["LANG"] == "en_US.UTF-8"
    assert env["TZ"] == "UTC" and env["SYSTEMROOT"] == "C:\\Windows"
    assert env["LC_ALL"] == "C" and env["LC_TIME"] == "en_GB"
    assert not [name for name in env if "SECRET" in name or "TOKEN" in name or "KEY" in name]
    assert "FILES_ROOT" not in env


def test_home_and_the_temporary_directories_are_the_throwaway_directory() -> None:
    env = build(workdir="/work/dir")
    assert [env[name] for name in ("HOME", "TMPDIR", "TEMP", "TMP")] == ["/work/dir"] * 4


def test_a_named_variable_is_passed_with_its_value() -> None:
    env = build("FILES_ROOT", "TOKEN")
    assert env["FILES_ROOT"] == "/data" and env["TOKEN"] == "tok"


def test_naming_a_variable_the_allow_list_already_has_is_harmless() -> None:
    assert build("PATH")["PATH"] == "/usr/bin:/bin"


def test_a_named_variable_that_is_not_set_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        build("NOT_SET_ANYWHERE")
    assert (error.value.code, error.value.http_status) == ("TOOL_ENV_MISSING", 422)
    assert error.value.message == "the environment variable NOT_SET_ANYWHERE is not set"


@pytest.mark.parametrize("name", ["HOME", "TMPDIR", "TEMP", "TMP"])
def test_the_confined_names_cannot_be_passed_on(name: str) -> None:
    with pytest.raises(ApplicationError) as error:
        build(name)
    assert (error.value.code, error.value.http_status) == ("TOOL_ENV_RESERVED", 422)


def test_the_result_is_a_new_dict_each_time() -> None:
    environment = ServerEnvironment(PARENT)
    first = environment.build((), Path("/w"))
    first["PATH"] = "changed"
    assert environment.build((), Path("/w"))["PATH"] == "/usr/bin:/bin"
    assert PARENT["PATH"] == "/usr/bin:/bin"


def test_without_an_environment_given_it_reads_the_real_one() -> None:
    assert ServerEnvironment().build((), Path("/w"))["PATH"] == os.environ["PATH"]
