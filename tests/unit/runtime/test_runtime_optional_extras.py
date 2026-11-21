"""The server commands must work in an install that has none of the publishing libraries."""

import subprocess
import sys
import textwrap

import pytest

BLOCKED = ("PIL", "numpy", "pypdf", "pdfplumber", "markdown_it", "defusedxml")


def run_without_extras(
    code: str, env: dict[str, str] | None = None, blocked: tuple[str, ...] = BLOCKED
) -> subprocess.CompletedProcess[str]:
    """Run code in a fresh interpreter where the optional libraries cannot be imported."""
    prelude = f"import sys\nfor name in {blocked!r}:\n    sys.modules[name] = None\n"
    return subprocess.run(
        [sys.executable, "-c", prelude + textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )


def test_the_cli_imports_without_the_publishing_libraries() -> None:
    result = run_without_extras("import engineering_influence.runtime.cli_runtime")

    assert result.returncode == 0, result.stderr


def test_serve_reports_missing_settings_instead_of_crashing_on_import() -> None:
    result = run_without_extras(
        """
        import os
        os.environ.pop("EI_DATABASE_URL", None)
        os.environ.pop("EI_RABBITMQ_URL", None)
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(["serve", "api"]))
        """
    )

    assert result.returncode == 2
    assert "EI_DATABASE_URL" in result.stderr
    assert "Traceback" not in result.stderr


def test_the_pipeline_command_works_without_the_publishing_libraries() -> None:
    result = run_without_extras(
        """
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(
            ["pipeline", "start", "--slug", "demo", "--title", "Demo", "--postulate", "x"]
        ))
        """
    )

    assert result.returncode == 0, result.stderr
    assert "project_slug" in result.stdout


def test_a_book_command_without_the_extra_explains_how_to_install_it() -> None:
    result = run_without_extras(
        """
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(["book", "audit"]))
        """
    )

    assert result.returncode == 1
    assert "pip install 'engineering-influence[publishing]'" in result.stderr
    # It names the first missing library of the extra; which one that is depends on import order.
    assert any(f"({name} is missing)" in result.stderr for name in BLOCKED)
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "module",
    ["engineering_influence.runtime.api_runtime", "engineering_influence.runtime.worker_runtime"],
)
def test_the_runtime_roots_import_without_the_publishing_libraries(module: str) -> None:
    result = run_without_extras(f"import {module}")

    assert result.returncode == 0, result.stderr


def test_serve_without_the_runtime_extra_explains_how_to_install_it() -> None:
    result = run_without_extras(
        """
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(["serve", "worker"]))
        """,
        blocked=("vibey_bootstrap", "aio_pika", "sqlmodel", "uvicorn"),
    )

    assert result.returncode == 1
    assert "pip install 'engineering-influence[api,runtime]'" in result.stderr
    assert "is missing" in result.stderr
    assert "Traceback" not in result.stderr


def test_db_without_the_runtime_extra_explains_how_to_install_it() -> None:
    result = run_without_extras(
        """
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(["db", "upgrade"]))
        """,
        blocked=("vibey_bootstrap", "alembic", "sqlalchemy", "sqlmodel"),
    )

    assert result.returncode == 1
    assert "pip install 'engineering-influence[runtime]'" in result.stderr
    assert "is missing" in result.stderr
    assert "Traceback" not in result.stderr


def test_run_commands_without_the_runtime_extra_explain_how_to_install_it() -> None:
    result = run_without_extras(
        """
        from engineering_influence.runtime.cli_runtime import CliRuntime
        raise SystemExit(CliRuntime().build().run(["run", "cancel", "run-1"]))
        """,
        blocked=("vibey_bootstrap", "alembic", "sqlalchemy", "sqlmodel"),
    )

    assert result.returncode == 1
    assert "pip install 'engineering-influence[runtime]'" in result.stderr
    assert "is missing" in result.stderr
    assert "Traceback" not in result.stderr
