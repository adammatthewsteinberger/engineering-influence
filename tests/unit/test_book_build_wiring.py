"""The pieces that connect the build stage to the publishing code, and the setting that asks for a strict release."""

import os
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.build.temp_project_manuscript_builder import (
    TempProjectManuscriptBuilder,
)
from engineering_influence.infrastructure.scratch_project import ScratchProject
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.controller_book_publisher import ControllerBookPublisher
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime


class NoSecrets(SecretProviderInterface):
    def require(self, name: str) -> str:
        raise ApplicationError(code="SECRET_MISSING", message=name)


class Controller:
    """Records what the publisher asks of the controller."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def publish(self, slug: str, **options: Any) -> tuple[dict[str, Any], bool]:
        self.calls.append(("publish", (slug, options)))
        return {"status": "pass"}, True

    def package(self, slug: str) -> str:
        self.calls.append(("package", slug))
        return "packaged"


def test_the_publisher_hands_publish_and_package_to_the_controller() -> None:
    controller = Controller()
    publisher = ControllerBookPublisher(controller)  # type: ignore[arg-type]
    assert publisher.publish("herbs", no_render=True, strict_release=True) == (
        {"status": "pass"},
        True,
    )
    assert publisher.package("herbs") == "packaged"
    assert controller.calls == [
        ("publish", ("herbs", {"no_render": True, "strict_release": True})),
        ("package", "herbs"),
    ]


def test_the_runtime_builds_a_publisher_for_a_project_folder(tmp_path: Path) -> None:
    assert isinstance(StageExecutorRuntime._publisher(tmp_path), ControllerBookPublisher)


def runtime(**environment: str) -> StageExecutorRuntime:
    return StageExecutorRuntime(environment, NoSecrets(), date(2026, 11, 22))


@pytest.mark.parametrize(
    ("value", "strict"),
    [
        (None, False),
        ("", False),
        ("0", False),
        ("no", False),
        ("1", True),
        ("true", True),
        (" YES ", True),
    ],
)
def test_a_strict_release_is_built_only_when_the_environment_asks_for_one(
    value: str | None, strict: bool
) -> None:
    environment = {} if value is None else {"EI_BUILD_STRICT_RELEASE": value}
    built = runtime(**environment)._book_builder()
    assert isinstance(built, TempProjectManuscriptBuilder)
    assert built._strict_release is strict


def test_a_builder_that_was_given_is_the_one_used() -> None:
    given = TempProjectManuscriptBuilder(lambda root: None)  # type: ignore[arg-type, return-value]
    assert (
        StageExecutorRuntime({}, NoSecrets(), date(2026, 11, 22), builder=given)._book_builder()
        is given
    )


def test_the_files_of_a_project_are_written_below_the_folder(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    ScratchProject.write(root, {"books/a.toml": b"a", "src/deep/b.md": b"b"})
    assert (root / "books" / "a.toml").read_bytes() == b"a"
    assert (root / "src" / "deep" / "b.md").read_bytes() == b"b"


@pytest.mark.parametrize("name", ["../out.md", "/etc/passwd", "a/../../out.md", "."])
def test_a_path_that_would_leave_the_folder_is_refused(tmp_path: Path, name: str) -> None:
    root = tmp_path.resolve()
    with pytest.raises(ValueError, match="would leave the project"):
        ScratchProject.write(root, {name: b"x"})
    assert not any(p.is_file() for p in tmp_path.parent.glob("out.md"))
    assert os.listdir(root) == []
