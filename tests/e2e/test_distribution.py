"""Build and install the real artifacts. Run with: pytest -m distribution (needs network)."""

import hashlib
import os
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

import engineering_influence

pytestmark = pytest.mark.distribution

ROOT = Path(__file__).resolve().parents[2]
VERSION = engineering_influence.__version__
ASSETS = "engineering_influence/publishing/assets/"


def run(
    *command: str | Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
        env=env,
        cwd=ROOT,
    )


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    for package in ([], ["--package", "engineering-influence-sdk"]):
        built = run("uv", "build", *package, "--out-dir", out)
        assert built.returncode == 0, built.stderr
    return out


def wheel(dist: Path, prefix: str = "engineering_influence-") -> Path:
    return next(dist.glob(f"{prefix}*.whl"))


def sdist(dist: Path) -> Path:
    return next(dist.glob("engineering_influence-*.tar.gz"))


@pytest.fixture
def clean_env(tmp_path: Path) -> Iterator[Path]:
    """A fresh virtual environment with nothing installed."""
    created = run("uv", "venv", "--python", sys.executable, tmp_path / "venv")
    assert created.returncode == 0, created.stderr
    yield tmp_path / "venv"


def install(env: Path, requirement: str) -> None:
    done = run("uv", "pip", "install", "--python", env / "bin" / "python", requirement)
    assert done.returncode == 0, done.stderr


def ei(env: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return run(env / "bin" / "ei", *arguments, env={"PATH": "/usr/bin:/bin"})


def test_the_wheel_ships_the_typing_marker_the_assets_and_their_licenses(dist: Path) -> None:
    names = set(zipfile.ZipFile(wheel(dist)).namelist())

    assert "engineering_influence/py.typed" in names
    for needed in (
        "fine-book.cls",
        "fine-book-hardcover.cls",
        "fine-ebook.css",
        "fonts/EBGaramond-Regular.otf",
        "fonts/OFL-EBGaramond.txt",
        "fonts/OFL-Libertinus.txt",
        "fonts/LICENSE-DejaVu.txt",
    ):
        assert ASSETS + needed in names, needed
    assert any(name.endswith("dist-info/licenses/LICENSE") for name in names)


def test_the_wheel_holds_only_the_package(dist: Path) -> None:
    names = zipfile.ZipFile(wheel(dist)).namelist()

    stray = [
        n for n in names if not n.startswith(("engineering_influence/", "engineering_influence-"))
    ]
    assert stray == []


def test_the_sdist_contains_the_source_and_nothing_local(dist: Path) -> None:
    with tarfile.open(sdist(dist)) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}

    for needed in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "src/engineering_influence/__init__.py",
    ):
        assert needed in names, needed
    leaked = [
        name
        for name in names
        if name.startswith(
            (".githooks", ".github", ".import_linter_cache", ".venv", "examples", "uv.lock")
        )
        or name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "Dockerfile", ".vibey-gh.toml"}
        or name.endswith((".env", ".pyc"))
    ]
    assert leaked == []


def test_the_build_is_reproducible(tmp_path: Path) -> None:
    """The same source and timestamp must give byte-identical files, so anyone can verify them."""
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "1700000000"}
    digests = []
    for attempt in ("first", "second"):
        out = tmp_path / attempt
        built = run("uv", "build", "--out-dir", out, env=environment)
        assert built.returncode == 0, built.stderr
        digests.append(
            {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(out.glob("*.*"))
                if path.suffix in {".whl", ".gz"}
            }
        )

    assert digests[0] == digests[1]
    assert len(digests[0]) == 2


def test_the_metadata_describes_the_project(dist: Path) -> None:
    zf = zipfile.ZipFile(wheel(dist))
    text = zf.read(next(n for n in zf.namelist() if n.endswith("METADATA"))).decode()

    assert f"Version: {VERSION}" in text
    assert "License-Expression: MIT" in text
    assert "Classifier: Typing :: Typed" in text
    assert "Requires-Python: >=3.12" in text
    assert (
        "Project-URL: Source, https://github.com/adammatthewsteinberger/engineering-influence"
        in text
    )
    assert "Provides-Extra: publishing" in text and "Provides-Extra: runtime" in text


def test_a_minimal_install_runs_the_server_commands(dist: Path, clean_env: Path) -> None:
    install(clean_env, str(wheel(dist)))

    version = ei(clean_env, "--version")
    started = ei(
        clean_env, "pipeline", "start", "--slug", "demo", "--title", "Demo", "--postulate", "x"
    )
    served = ei(clean_env, "serve", "api")

    assert version.stdout.strip() == f"engineering-influence {VERSION}"
    assert started.returncode == 0 and "project_slug" in started.stdout
    assert served.returncode == 1
    assert "engineering-influence[api,runtime]" in served.stderr
    assert "Traceback" not in served.stderr


def test_the_api_and_runtime_extras_are_enough_to_serve(dist: Path, clean_env: Path) -> None:
    install(clean_env, f"{wheel(dist)}[api,runtime]")

    unconfigured = ei(clean_env, "serve", "api")

    assert unconfigured.returncode == 2
    assert "EI_DATABASE_URL" in unconfigured.stderr and "Traceback" not in unconfigured.stderr


def test_book_commands_ask_for_the_extra_when_it_is_missing(dist: Path, clean_env: Path) -> None:
    install(clean_env, str(wheel(dist)))

    result = ei(clean_env, "book", "audit")

    assert result.returncode == 1
    assert "engineering-influence[publishing]" in result.stderr


def test_the_publishing_extra_makes_the_book_commands_and_assets_available(
    dist: Path, clean_env: Path
) -> None:
    install(clean_env, f"{wheel(dist)}[publishing]")

    helped = ei(clean_env, "book", "--help")
    located = run(
        clean_env / "bin" / "python",
        "-c",
        "from importlib.resources import files;"
        "root = files('engineering_influence.publishing') / 'assets';"
        "print((root / 'fine-book.cls').is_file(), (root / 'fonts' / 'EBGaramond-Regular.otf').is_file())",
    )

    assert helped.returncode == 0, helped.stderr
    assert located.stdout.strip() == "True True"


def test_the_sdk_installs_alone_and_matches_the_core_version(dist: Path, clean_env: Path) -> None:
    install(clean_env, str(wheel(dist, "engineering_influence_sdk-")))

    result = run(
        clean_env / "bin" / "python",
        "-c",
        "import engineering_influence_sdk as s; print(s.__version__, s.EngineeringInfluenceClient.__name__)",
    )

    assert result.stdout.strip() == f"{VERSION} EngineeringInfluenceClient"


def test_the_type_marker_is_installed(dist: Path, clean_env: Path) -> None:
    install(clean_env, str(wheel(dist)))

    result = run(
        clean_env / "bin" / "python",
        "-c",
        "from importlib.resources import files;print((files('engineering_influence') / 'py.typed').is_file())",
    )

    assert result.stdout.strip() == "True"
