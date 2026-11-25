"""The documentation workflow builds strictly on every change and publishes only when it is switched on."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def workflow() -> dict[str, object]:
    return yaml.safe_load((ROOT / ".github/workflows/docs.yml").read_text())  # type: ignore[no-any-return]


def jobs() -> dict[str, dict[str, object]]:
    found = workflow()["jobs"]
    assert isinstance(found, dict)
    return found


def steps(job: str) -> list[dict[str, object]]:
    found = jobs()[job]["steps"]
    assert isinstance(found, list)
    return found


def triggers() -> dict[str, object]:
    found = workflow().get("on", workflow().get(True))
    assert isinstance(found, dict)
    return found


def test_it_runs_on_a_pull_request_on_develop_and_by_hand_and_never_on_main_or_a_tag() -> None:
    assert set(triggers()) == {"pull_request", "push", "workflow_dispatch"}
    assert triggers()["push"]["branches"] == ["develop"]  # type: ignore[index]


def test_a_change_to_the_documents_or_the_tools_that_build_them_starts_it() -> None:
    paths = triggers()["push"]["paths"]  # type: ignore[index]

    assert paths == triggers()["pull_request"]["paths"]  # type: ignore[index]
    for expected in (
        "docs/**",
        "README.md",
        "properdocs.yml",
        "scripts/build_docs_site.py",
        "scripts/inject_docs_meta.py",
        "docs-site/**",
        "llms.txt",
        ".github/workflows/docs.yml",
    ):
        assert expected in paths, expected


def test_the_build_is_strict_so_a_link_that_goes_nowhere_fails_it() -> None:
    commands = " ".join(str(step.get("run", "")) for step in steps("build"))

    assert "properdocs build --strict" in commands
    assert "properdocs==1.6.7" in commands and "properdocs-theme-mkdocs==1.6.7" in commands
    assert (
        commands.index("build_docs_site.py")
        < commands.index("properdocs build")
        < commands.index("inject_docs_meta.py")
    )


def test_the_build_uses_the_locked_environment() -> None:
    commands = [str(step.get("run", "")) for step in steps("build")]

    assert "uv sync --locked --extra runtime" in commands


def test_a_pull_request_publishes_nothing_it_only_builds() -> None:
    upload = next(
        step for step in steps("build") if "upload-pages-artifact" in str(step.get("uses", ""))
    )
    assert upload["if"] == "github.event_name != 'pull_request'"

    condition = " ".join(str(jobs()["deploy"]["if"]).split())
    assert condition == "github.event_name != 'pull_request' && vars.PUBLISH_DOCS == 'true'"
    assert jobs()["deploy"]["needs"] == "build"


def test_publishing_has_its_own_environment_and_only_the_permissions_pages_needs() -> None:
    deploy = jobs()["deploy"]

    assert deploy["environment"]["name"] == "github-pages"  # type: ignore[index]
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert jobs()["build"]["permissions"] == {"contents": "read"}
    assert workflow()["permissions"] == {}


def test_the_checkout_keeps_no_credentials() -> None:
    checkout = steps("build")[0]

    assert "actions/checkout" in str(checkout["uses"]) and checkout["with"] == {
        "persist-credentials": False
    }  # type: ignore[comparison-overlap]


@pytest.mark.parametrize("job", ["build", "deploy"])
def test_every_action_is_pinned_to_a_full_commit_sha(job: str) -> None:
    used = [str(step["uses"]) for step in steps(job) if "uses" in step]

    assert used
    for reference in used:
        _, _, ref = reference.partition("@")
        assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), reference


def test_nothing_the_run_does_not_control_reaches_a_script() -> None:
    text = (ROOT / ".github/workflows/docs.yml").read_text()

    assert "github.event.pull_request" not in text and "github.head_ref" not in text
    assert "analytics" not in text.lower().replace("no analytics", "")
