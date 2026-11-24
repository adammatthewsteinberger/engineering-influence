# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""``install.sh``: the one command that installs what a book needs, run here against stand-in tools."""

import re
import shutil
import stat
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "install.sh"
REAL = ("sh", "cat", "mkdir", "tr", "od", "chmod", "cp", "basename", "dirname")
GIT = "git+https://github.com/adammatthewsteinberger/engineering-influence"
RAW = "https://raw.githubusercontent.com/adammatthewsteinberger/engineering-influence"

# One stand-in serves every tool: it records the call, then behaves as the FAKE_* variables say.
STAND_IN = """#!/bin/sh
name="$(basename "$0")"
echo "$name $*" >> "$FAKE_LOG"
case " $FAKE_FAIL " in *" $name "*) echo "$name: failed on purpose" >&2; exit 1 ;; esac
case "$name" in
  uname) echo "$FAKE_SYSTEM" ;;
  id) echo "$FAKE_UID" ;;
  sudo) exec "$@" ;;
  sleep) : ;;
  ei) exit "$FAKE_DOCTOR" ;;
  docker) [ "$1 $2" != "compose version" ] || exit "$FAKE_COMPOSE" ;;
  curl)
    out=""
    url=""
    while [ "$#" -gt 0 ]; do
      case "$1" in -o) out="$2"; shift ;; http*) url="$1" ;; esac
      shift
    done
    case "$url" in
      https://astral.sh/uv/install.sh)
        echo "mkdir -p \\"$HOME/.local/bin\\" && cp \\"$FAKE_BIN/stand-in\\" \\"$HOME/.local/bin/uv\\"" ;;
      https://ollama.com/install.sh) echo "cp \\"$FAKE_BIN/stand-in\\" \\"$FAKE_BIN/ollama\\"" ;;
      http://127.0.0.1:11434/api/tags) exit "$FAKE_OLLAMA" ;;
      *) [ -z "$out" ] || echo "fetched from $url" > "$out" ;;
    esac ;;
esac
"""


class Machine:
    """A pretend machine: a home folder and a ``PATH`` that holds only the tools a test put there."""

    def __init__(self, tmp_path: Path, system: str, tools: tuple[str, ...]) -> None:
        self.home = tmp_path / "home"
        self.bin = tmp_path / "bin"
        self.log = tmp_path / "calls.log"
        self.system = system
        self.home.mkdir()
        self.bin.mkdir()
        self.log.write_text("")
        stand_in = self.bin / "stand-in"
        stand_in.write_text(STAND_IN)
        stand_in.chmod(stand_in.stat().st_mode | stat.S_IEXEC)
        for name in REAL:
            found = shutil.which(name)
            assert found, name
            (self.bin / name).symlink_to(found)
        for name in ("uname", "id", "sudo", "sleep", "curl", "ei", *tools):
            self.add(name)

    def add(self, name: str) -> None:
        shutil.copy(self.bin / "stand-in", self.bin / name)

    def install(self, *options: str, **settings: str) -> subprocess.CompletedProcess[str]:
        environment = {
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "FAKE_LOG": str(self.log),
            "FAKE_BIN": str(self.bin),
            "FAKE_SYSTEM": self.system,
            "FAKE_UID": "501",
            "FAKE_DOCTOR": "0",
            "FAKE_COMPOSE": "0",
            "FAKE_OLLAMA": "0",
            "FAKE_FAIL": "",
        }
        environment.update(settings)
        shell = shutil.which("sh")
        assert shell
        return subprocess.run(
            [shell, str(SCRIPT), *options],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )

    def calls(self, *ignored: str) -> list[str]:
        skip = ("uname", "id", *ignored)
        return [c for c in self.log.read_text().splitlines() if c.split()[0] not in skip]

    @property
    def profile(self) -> Path:
        return self.home / ".config" / "engineering-influence" / "author.toml"

    @property
    def search(self) -> Path:
        return self.home / ".config" / "engineering-influence" / "searxng"


MAC_TOOLS = ("brew", "uv", "launchctl", "ollama", "docker")
LINUX_TOOLS = ("apt-get", "uv", "ollama", "docker")
PROBE = "curl -fsS -m 2 http://127.0.0.1:11434/api/tags"
UV_INSTALL = f"uv tool install --force engineering-influence[runtime,publishing,mcp] @ {GIT}@main"


@pytest.fixture
def mac(tmp_path: Path) -> Machine:
    return Machine(tmp_path, "Darwin", MAC_TOOLS)


@pytest.fixture
def linux(tmp_path: Path) -> Machine:
    return Machine(tmp_path, "Linux", LINUX_TOOLS)


# ------------------------------------------------------------------------------ the whole install
def test_on_a_mac_it_installs_each_part_in_order_then_checks_the_machine(mac: Machine) -> None:
    done = mac.install()

    assert done.returncode == 0, done.stderr
    assert mac.calls("curl", "docker") == [
        UV_INSTALL,
        "launchctl setenv OLLAMA_CONTEXT_LENGTH 32768",
        "ollama pull gpt-oss:20b",
        "brew install --cask mactex-no-gui",
        "brew install poppler",
        "brew install epubcheck",
        "ei doctor --ready",
    ]
    for step in ("1 of 6", "2 of 6", "3 of 6", "4 of 6", "5 of 6", "6 of 6"):
        assert f"==> {step}" in done.stdout


def test_on_linux_the_tex_packages_are_the_ones_the_worker_image_installs(linux: Machine) -> None:
    done = linux.install()

    assert done.returncode == 0, done.stderr
    update, install = [c for c in linux.calls() if c.startswith("sudo apt-get")]
    assert update == "sudo apt-get update"
    assert install.startswith("sudo apt-get install -y --no-install-recommends ")
    dockerfile = (ROOT / "Dockerfile").read_text()
    wanted = re.search(r"--no-install-recommends \\\n(.*?)\n && rm", dockerfile, re.DOTALL)
    assert wanted
    assert sorted(install.split()[5:]) == sorted(wanted.group(1).replace("\\", " ").split())


def test_on_linux_ollama_is_pulled_and_its_context_is_left_for_the_person_to_set(
    linux: Machine,
) -> None:
    done = linux.install()

    assert "ollama pull gpt-oss:20b" in linux.calls()
    assert not any(c.startswith("launchctl") for c in linux.calls())
    assert "Environment=OLLAMA_CONTEXT_LENGTH=32768" in done.stdout


def test_root_installs_packages_without_sudo(linux: Machine) -> None:
    linux.install(FAKE_UID="0")

    assert "apt-get update" in linux.calls()
    assert not any(c.startswith("sudo") for c in linux.calls())


def test_the_machine_is_checked_with_the_profile_that_was_just_written(mac: Machine) -> None:
    done = mac.install()

    assert "ei doctor --ready" in mac.calls()
    assert f"--profile {mac.profile}" in done.stdout
    assert 'ei book create --kind nonfiction "your idea" --budget-usd 5' in done.stdout


def test_a_failed_readiness_check_is_the_installers_exit_status_and_the_next_steps_still_print(
    mac: Machine,
) -> None:
    done = mac.install(FAKE_DOCTOR="1")

    assert done.returncode == 1
    assert "Some checks above failed" in done.stdout and "2. Write a book:" in done.stdout


def test_a_passing_check_says_nothing_about_failures(mac: Machine) -> None:
    assert "Some checks above failed" not in mac.install().stdout


# ------------------------------------------------------------------------------ what is already there
def test_tools_that_are_already_installed_are_not_installed_again(mac: Machine) -> None:
    for name in ("lualatex", "latexmk", "tex4ebook", "pdftoppm", "epubcheck"):
        mac.add(name)

    mac.install()

    assert not any(c.startswith("brew install") for c in mac.calls())


@pytest.mark.parametrize("missing", ["lualatex", "latexmk", "tex4ebook"])
def test_one_missing_tex_tool_is_enough_to_install_tex(mac: Machine, missing: str) -> None:
    for name in {"lualatex", "latexmk", "tex4ebook"} - {missing}:
        mac.add(name)

    mac.install()

    assert "brew install --cask mactex-no-gui" in mac.calls()


def test_a_missing_ollama_is_installed_with_homebrew_on_a_mac(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Darwin", ("brew", "uv", "launchctl", "docker"))
    machine.add("ollama")  # the pull needs it afterwards, as a real install would provide
    (machine.bin / "ollama").unlink()

    done = machine.install()

    assert "brew install ollama" in machine.calls()
    assert (
        done.returncode != 0
    )  # the stand-in brew installs nothing, so the pull has no ollama to call


def test_a_missing_ollama_is_installed_with_its_own_script_on_linux(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Linux", ("apt-get", "uv", "docker"))

    done = machine.install()

    assert done.returncode == 0, done.stderr
    assert "curl -fsSL https://ollama.com/install.sh" in machine.calls()
    assert "ollama pull gpt-oss:20b" in machine.calls()


def test_a_missing_uv_is_installed_first_and_then_used(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Darwin", ("brew", "launchctl", "ollama", "docker"))

    done = machine.install()

    assert done.returncode == 0, done.stderr
    calls = machine.calls()
    assert calls.index("curl -fsSL https://astral.sh/uv/install.sh") < calls.index(UV_INSTALL)
    assert (machine.home / ".local" / "bin" / "uv").is_file()


def test_an_author_profile_that_exists_is_never_written_over(mac: Machine) -> None:
    mac.profile.parent.mkdir(parents=True)
    mac.profile.write_text('author = "Someone Real"\n')

    done = mac.install()

    assert mac.profile.read_text() == 'author = "Someone Real"\n'
    assert "is already there and was left as it is" in done.stdout


def test_the_starter_profile_is_private_and_matches_the_example_in_the_repository(
    mac: Machine,
) -> None:
    mac.install()

    written = tomllib.loads(mac.profile.read_text())
    example = tomllib.loads((ROOT / "examples" / "author-profile.example.toml").read_text())
    assert written == example
    assert stat.S_IMODE(mac.profile.stat().st_mode) == 0o600


def test_a_second_run_changes_nothing_that_is_in_place(mac: Machine) -> None:
    mac.install()
    profile, secret = mac.profile.read_text(), (mac.search / ".env").read_text()

    done = mac.install()

    assert done.returncode == 0, done.stderr
    assert mac.profile.read_text() == profile and (mac.search / ".env").read_text() == secret


# ------------------------------------------------------------------------------ the search
def test_with_docker_a_local_search_is_started_from_the_repositorys_own_files(mac: Machine) -> None:
    done = mac.install()

    compose, settings = mac.search / "docker-compose.yml", mac.search / "settings.yml"
    assert compose.read_text() == f"fetched from {RAW}/main/examples/searxng/docker-compose.yml\n"
    assert settings.read_text() == f"fetched from {RAW}/main/examples/searxng/settings.yml\n"
    assert (
        f"docker compose -f {compose} --env-file {mac.search / '.env'} up -d --wait" in mac.calls()
    )
    assert done.returncode == 0


def test_the_search_secret_is_generated_private_and_never_printed(mac: Machine) -> None:
    done = mac.install()

    env = mac.search / ".env"
    secret = env.read_text().strip().removeprefix("SEARXNG_SECRET=")
    assert re.fullmatch(r"[0-9a-f]{64}", secret)
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    assert secret not in done.stdout + done.stderr + mac.log.read_text()


def test_without_docker_compose_no_search_is_started_and_the_person_is_told_what_to_set(
    mac: Machine,
) -> None:
    done = mac.install(FAKE_COMPOSE="1")

    assert done.returncode == 0, done.stderr
    assert not mac.search.exists()
    assert not any(c.startswith("docker compose -f") for c in mac.calls())
    assert "Set EI_SEARXNG_URL (a SearXNG you run) or BRAVE_SEARCH_API_KEY" in done.stdout


def test_a_machine_with_no_docker_at_all_is_handled_the_same_way(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Darwin", ("brew", "uv", "launchctl", "ollama"))

    done = machine.install()

    assert done.returncode == 0, done.stderr
    assert "Docker with compose is not here" in done.stdout


# ------------------------------------------------------------------------------ the options
def test_a_dry_run_prints_every_command_and_changes_nothing(mac: Machine) -> None:
    done = mac.install("--dry-run")

    assert done.returncode == 0, done.stderr
    # It may look (is compose there, is Ollama answering) but it changes nothing.
    assert mac.calls("docker") == [PROBE]
    assert not mac.profile.exists() and not mac.search.exists()
    for line in (
        f"+ {UV_INSTALL}",
        "+ ollama pull gpt-oss:20b",
        "+ brew install --cask mactex-no-gui",
        f"+ write {mac.profile}",
        f"+ EI_AUTHOR_PROFILE={mac.profile} ei doctor --ready",
    ):
        assert line in done.stdout
    assert "dry run: every command is printed and nothing is changed" in done.stdout


def test_a_dry_run_with_no_uv_says_how_it_would_be_installed_and_installs_nothing(
    tmp_path: Path,
) -> None:
    machine = Machine(tmp_path, "Darwin", ("brew", "launchctl", "ollama", "docker"))

    done = machine.install("--dry-run")

    assert "+ curl -fsSL https://astral.sh/uv/install.sh | sh" in done.stdout
    assert machine.calls("docker") == [PROBE]


def test_skip_model_leaves_ollama_alone(mac: Machine) -> None:
    done = mac.install("--skip-model")

    assert not any(c.startswith(("ollama", "launchctl", "brew services")) for c in mac.calls())
    assert "skipped (--skip-model)" in done.stdout and "13 GB" not in done.stdout


def test_skip_tex_installs_no_tex_and_says_what_will_then_fail(mac: Machine) -> None:
    done = mac.install("--skip-tex")

    assert not any(c.startswith("brew install") for c in mac.calls())
    assert "the last stage, build, will fail" in done.stdout


def test_skip_search_starts_no_search(mac: Machine) -> None:
    mac.install("--skip-search")

    assert not mac.search.exists() and not any(c.startswith("docker") for c in mac.calls())


def test_the_claude_code_skill_is_installed_only_when_asked_for(mac: Machine) -> None:
    mac.install()
    skill = mac.home / ".claude" / "skills" / "engineering-influence" / "SKILL.md"
    assert not skill.exists()

    mac.install("--with-claude-skill")

    assert skill.read_text() == (
        f"fetched from {RAW}/main/examples/claude-code/engineering-influence/SKILL.md\n"
    )


def test_version_chooses_what_is_installed_and_where_the_files_come_from(mac: Machine) -> None:
    mac.install("--version", "v1.2.3", "--with-claude-skill")

    assert (
        f"uv tool install --force engineering-influence[runtime,publishing,mcp] @ {GIT}@v1.2.3"
        in (mac.calls())
    )
    assert (
        f"{RAW}/v1.2.3/examples/searxng/settings.yml" in (mac.search / "settings.yml").read_text()
    )


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (("--everything",), "unknown option --everything"),
        (("--version",), "--version needs a tag, branch or commit"),
        (("--version", "v1; rm -rf ~"), "is not a tag, branch or commit"),
        (("--version", "--dry-run"), "is not a tag, branch or commit"),
        (("--version", ""), "is not a tag, branch or commit"),
    ],
)
def test_a_bad_option_exits_2_before_anything_runs(
    mac: Machine, options: tuple[str, ...], message: str
) -> None:
    done = mac.install(*options)

    assert done.returncode == 2 and message in done.stderr
    assert mac.calls() == []


# ------------------------------------------------------------------------------ where it stops
def test_a_system_it_does_not_know_stops_with_what_to_do_by_hand(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "FreeBSD", MAC_TOOLS)

    done = machine.install()

    assert done.returncode == 1 and machine.calls() == []
    assert "FreeBSD is not supported" in done.stderr and "GETTING_STARTED.md" in done.stderr


def test_a_mac_without_homebrew_stops_before_anything_is_installed(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Darwin", ("uv", "ollama", "docker"))

    done = machine.install()

    assert done.returncode == 1 and machine.calls() == []
    assert "https://brew.sh" in done.stderr


def test_linux_without_apt_stops_unless_both_package_steps_are_skipped(tmp_path: Path) -> None:
    machine = Machine(tmp_path, "Linux", ("uv", "ollama", "docker"))

    refused = machine.install()
    assert refused.returncode == 1 and machine.calls() == []
    assert "--skip-tex --skip-model" in refused.stderr
    assert machine.install("--skip-tex").returncode == 1
    assert machine.install("--skip-model").returncode == 1

    allowed = machine.install("--skip-tex", "--skip-model")
    assert allowed.returncode == 0, allowed.stderr
    assert UV_INSTALL in machine.calls()


@pytest.mark.parametrize(
    ("failing", "never_reached"),
    [
        ("uv", "ollama"),
        ("ollama", "brew install"),
        ("brew", "ei doctor"),
        ("launchctl", "ollama pull"),
    ],
)
def test_a_step_that_fails_stops_everything_after_it(
    mac: Machine, failing: str, never_reached: str
) -> None:
    done = mac.install(FAKE_FAIL=failing)

    assert done.returncode != 0
    assert not any(c.startswith(never_reached) for c in mac.calls())


def test_an_ollama_that_never_answers_stops_the_install_before_the_pull(mac: Machine) -> None:
    done = mac.install(FAKE_OLLAMA="7")

    assert done.returncode == 1
    assert "Ollama did not answer at http://127.0.0.1:11434 within a minute" in done.stderr
    assert "ollama pull gpt-oss:20b" not in mac.calls()
    assert sum(c.startswith("sleep") for c in mac.calls()) == 29


# ------------------------------------------------------------------------------ the script itself
def test_the_script_is_plain_posix_shell_that_parses() -> None:
    shell = shutil.which("sh")
    assert shell
    assert SCRIPT.read_text().startswith("#!/bin/sh\n")
    assert subprocess.run([shell, "-n", str(SCRIPT)], check=False).returncode == 0
    assert stat.S_IMODE(SCRIPT.stat().st_mode) & stat.S_IXUSR


def test_the_script_documents_the_one_command_and_every_option_it_accepts() -> None:
    text = SCRIPT.read_text()
    header = text.split("set -eu", 1)[0]

    assert f"curl -fsSL {RAW}/main/install.sh | sh" in header
    accepted = set(re.findall(r"^\s+(--[a-z-]+)\)", text, re.MULTILINE))
    assert accepted == {
        "--dry-run",
        "--skip-model",
        "--skip-tex",
        "--skip-search",
        "--with-claude-skill",
        "--version",
    }
    for option in accepted:
        assert option in header


def test_nothing_is_downloaded_from_anywhere_but_the_four_named_sources() -> None:
    hosts = set(re.findall(r"https?://([A-Za-z0-9.-]+)", SCRIPT.read_text()))

    assert hosts == {
        "raw.githubusercontent.com",
        "github.com",
        "astral.sh",
        "ollama.com",
        "docs.astral.sh",
        "brew.sh",
        "127.0.0.1",
        "the-vibey-project.github.io",
        "vibewithadam.matthewsteinberger.com",
    }


@pytest.mark.parametrize(
    ("tools", "system", "source"),
    [
        (("brew", "launchctl", "ollama", "docker"), "Darwin", "https://astral.sh/uv/install.sh"),
        (("apt-get", "uv", "docker"), "Linux", "https://ollama.com/install.sh"),
    ],
)
def test_another_projects_installer_that_cannot_be_downloaded_is_never_run_as_an_empty_script(
    tmp_path: Path, tools: tuple[str, ...], system: str, source: str
) -> None:
    machine = Machine(tmp_path, system, tools)

    done = machine.install(FAKE_FAIL="curl")

    assert done.returncode == 1
    assert f"error: could not download {source}" in done.stderr
    after = (
        ("uv tool", "ollama pull", "ei doctor")
        if "astral" in source
        else ("ollama pull", "ei doctor")
    )
    assert not any(c.startswith(after) for c in machine.calls())


def test_a_failed_docker_compose_up_stops_the_install(mac: Machine) -> None:
    (mac.bin / "docker").write_text(
        '#!/bin/sh\necho "docker $*" >> "$FAKE_LOG"\n[ "$1 $2" = "compose version" ] && exit 0\nexit 1\n'
    )

    done = mac.install()

    assert done.returncode != 0
    assert "ei doctor --ready" not in mac.calls()


def test_an_ollama_that_is_already_answering_is_left_running_however_it_was_started(
    mac: Machine,
) -> None:
    done = mac.install()

    assert not any(c.startswith("brew services") for c in mac.calls())
    assert "Ollama is already running" in done.stdout


def test_an_ollama_that_is_not_answering_is_started_as_a_service(mac: Machine) -> None:
    mac.install(FAKE_OLLAMA="7")

    assert "brew services start ollama" in mac.calls()
