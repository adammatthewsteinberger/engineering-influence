# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The whole non-fiction plan, end to end, through the real runtime and HTTP adapter, against a scripted local server.

This is the free rehearsal of the paid smoke test: it proves every stage, the budget, the retry loop, the audit and the
folder the run is written to, without a real model. What it cannot say is whether a real model's answers are any good.
"""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from local_server import LocalServer, Reply, Seen
from smoke_run import DEFAULT_IDEA, RUN_ID, LiveSettings, SmokeReport, SmokeRun

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind

DESCRIPTION = " ".join(["Herbs are easier to keep alive indoors than most people think."] * 10)
OUTLINE = """## Chapter 1: Light
Purpose: Explain how much light herbs need.
Beats:
- Windows

## Chapter 2: Water
Purpose: Explain watering.
Beats:
- Drainage
"""
LISTING = (
    "Title: Herbs Indoors\nSubtitle: A calm guide to windowsill herbs\nDescription:\n"
    + DESCRIPTION
    + "\nKeywords:\n"
    + "".join(f"- keyword {n}\n" for n in range(7))
    + "Categories:\n- Books > Crafts, Hobbies & Home > Gardening & Landscape Design\n"
)
CHAPTER = re.compile(r'<untrusted name="chapter">\n(.*?)\n</untrusted>', re.DOTALL)
NUMBER = re.compile(r"Write chapter (\d+) of")
CATALOG = """
[[model]]
provider = "local"
model = "m"
family = "f"
context_window = 200000
max_output_tokens = 8192
usage_policy_url = "https://example.test/policy"

[[model.price]]
effective = "2026-01-01"
input = 1000000
output = 5000000
cache_read = 0
cache_write = 0
batch_discount_percent = 0
"""
PROFILE = """
[[profile]]
name = "writer"
adapter = "openai_compatible"
provider = "local"
model = "m"
base_url = "{url}"
"""
AUTHOR = (
    'author = "Smoke Author"\npublisher = "Smoke Press"\nedition = "First Edition"\n'
    'author_bio = "Writes for the test."\nyear = 2031\n'
)
BRIEF = {
    "idea": "How to keep herbs alive indoors",
    "title_hint": "Herbs Indoors",
    "target_words": 400,
}


class NoSecrets(SecretProviderInterface):
    def require(self, name: str) -> str:
        raise ApplicationError(code="SECRET_MISSING", message=f"{name} is not set")


def answer(user: str) -> str:
    if user.startswith("Write the brief"):
        return "BRIEF: a practical guide to growing herbs indoors."
    if user.startswith("Write the positioning"):
        return "POSITIONING: calm, practical and kind to beginners."
    if user.startswith("Research the book"):
        return "RESEARCH NOTES: herbs need six hours of light and drainage."
    if user.startswith("Write the chapter outline"):
        return OUTLINE
    if user.startswith("Write the store listing"):
        return LISTING
    if user.startswith("Summarise this chapter"):
        return "Herbs need light and drainage."
    for edit in ("Revise the structure", "Line-edit", "Copy-edit"):
        if user.startswith(edit):
            found = CHAPTER.search(user)
            assert found is not None
            return found.group(1) + " Edited."
    chapter = NUMBER.search(user)
    assert chapter is not None, user[:80]
    return f"# Chapter {chapter.group(1)}: Title\n\n" + " ".join(
        ["Herbs like a bright window."] * 12
    )


def reply(text: str) -> Reply:
    words = len(text.split())
    body = {
        "model": "gpt-snap",
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 500, "completion_tokens": max(words, 1)},
    }
    return 200, {"content-type": "application/json"}, json.dumps(body).encode()


def serve(failures: dict[str, int] | None = None) -> LocalServer:
    left = dict(failures or {})

    def route(request: Seen) -> Reply:
        messages = json.loads(request.body)["messages"]
        user = messages[-1]["content"]
        for opening, count in list(left.items()):
            if user.startswith(opening) and count > 0:
                left[opening] = count - 1
                return 503, {"content-type": "application/json"}, b'{"error": "busy"}'
        return reply(answer(user))

    return LocalServer(route)


def smoke(tmp_path: Path, url: str, cap: int = 5_000_000) -> SmokeRun:
    profiles, catalog, author = tmp_path / "p.toml", tmp_path / "c.toml", tmp_path / "a.toml"
    profiles.write_text(PROFILE.format(url=url), encoding="utf-8")
    catalog.write_text(CATALOG, encoding="utf-8")
    author.write_text(AUTHOR, encoding="utf-8")
    environment = {
        "EI_STAGE_EXECUTOR": "model",
        "EI_STAGE_MODEL_PROFILE": "writer",
        "EI_MODEL_PROFILES": str(profiles),
        "EI_MODEL_CATALOG": str(catalog),
        "EI_SEARXNG_URL": "http://127.0.0.1:1",
        "EI_AUTHOR_PROFILE": str(author),
    }
    brief = BookBrief(kind=BookKind.NONFICTION, budget_micro_usd=cap, **BRIEF)  # type: ignore[arg-type]
    return SmokeRun(environment, NoSecrets(), brief, date(2026, 11, 22))


def run(
    tmp_path: Path, cap: int = 5_000_000, failures: dict[str, int] | None = None
) -> SmokeReport:
    with serve(failures) as server:
        return smoke(tmp_path, server.url, cap).run()


def test_every_stage_of_the_plan_advances_and_the_run_completes(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert report.completed and report.status == "completed"
    assert [row.stage for row in report.rows] == [
        "brief",
        "positioning",
        "research",
        "outline",
        "metadata",
        "draft",
        "revise_structure",
        "revise_lines",
        "copy_edit",
        "assemble",
        "audit",
    ]
    assert [row.outcome for row in report.rows] == ["advanced"] * 10 + ["completed"]
    assert {row.attempts for row in report.rows} == {1}
    assert report.issues == ()


def test_spend_is_counted_per_stage_and_stays_under_the_cap(tmp_path: Path) -> None:
    report = run(tmp_path, cap=5_000_000)
    paid = {row.stage: row.spent_micro_usd for row in report.rows}
    assert all(paid[stage] > 0 for stage in ("brief", "outline", "draft", "copy_edit"))
    assert paid["assemble"] == 0 and paid["audit"] == 0
    assert sum(paid.values()) == report.spent_micro_usd
    assert 0 < report.spent_micro_usd <= report.cap_micro_usd


def test_the_book_the_run_made_is_in_the_artifacts_and_passes_the_audit(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert "manuscript/books/herbs-indoors.toml" in report.artifacts
    assert report.artifacts["manuscript/src/chapter_02.md"].startswith(b"# Water\n\nHerbs like")
    assert report.artifacts["copy_02.md"].endswith(b"Edited. Edited. Edited.")
    assert b"Status: pass" in report.artifacts["audit.md"]
    config = report.artifacts["manuscript/books/herbs-indoors.toml"].decode()
    assert 'author = "Smoke Author"' in config and 'title = "Herbs Indoors"' in config


def test_a_stage_the_provider_fails_once_is_retried_and_the_run_still_completes(
    tmp_path: Path,
) -> None:
    report = run(tmp_path, failures={"Write the chapter outline": 1})
    assert report.completed
    outline = next(row for row in report.rows if row.stage == "outline")
    assert (outline.attempts, outline.outcome) == (2, "advanced")


def test_a_cap_too_small_for_the_first_call_stops_the_run_with_nothing_spent(
    tmp_path: Path,
) -> None:
    report = run(tmp_path, cap=1)
    assert not report.completed and report.status == "failed"
    assert [(row.stage, row.outcome) for row in report.rows] == [("brief", "failed")]
    assert report.spent_micro_usd == 0
    assert any("budget" in issue.lower() or "cap" in issue.lower() for issue in report.issues)


def test_the_report_and_every_artifact_are_written_to_a_new_folder(tmp_path: Path) -> None:
    report = run(tmp_path)
    folder = tmp_path / "out"
    report.write(folder)
    summary = json.loads((folder / "smoke-report.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed" and summary["budget"]["cap_micro_usd"] == 5_000_000
    assert [row["stage"] for row in summary["stages"]][-1] == "audit"
    assert summary["budget"]["spent_usd"] == round(report.spent_micro_usd / 1_000_000, 4)
    assert (folder / "manuscript" / "src" / "chapter_01.md").is_file()
    assert (folder / "audit" / "release-readiness.json").is_file()
    assert RUN_ID not in "".join(summary["artifacts"])
    with pytest.raises(ApplicationError) as error:
        report.write(folder)
    assert error.value.code == "EXPORT_TARGET_NOT_EMPTY"


LIVE = {
    "EI_SMOKE_PROFILE": "writer",
    "EI_MODEL_PROFILES": "/p.toml",
    "EI_MODEL_CATALOG": "/c.toml",
    "EI_SMOKE_BUDGET_MICRO_USD": "3000000",
    "OTHER": "kept",
}


def test_live_settings_need_a_profile_its_files_and_a_cap_with_no_default(tmp_path: Path) -> None:
    for name in (
        "EI_SMOKE_PROFILE",
        "EI_MODEL_PROFILES",
        "EI_MODEL_CATALOG",
        "EI_SMOKE_BUDGET_MICRO_USD",
    ):
        without = {key: value for key, value in LIVE.items() if key != name}
        with pytest.raises(ValueError, match=f"set {name}"):
            LiveSettings.from_environment(without, tmp_path)
    blank = {**LIVE, "EI_SMOKE_BUDGET_MICRO_USD": "  "}
    with pytest.raises(ValueError, match="EI_SMOKE_BUDGET_MICRO_USD"):
        LiveSettings.from_environment(blank, tmp_path)


@pytest.mark.parametrize("bad", ["0", "-5", "three", "1.5", ""])
def test_the_cap_and_the_target_are_whole_numbers_above_zero(tmp_path: Path, bad: str) -> None:
    if bad:
        with pytest.raises(ValueError, match="whole number above zero"):
            LiveSettings.from_environment({**LIVE, "EI_SMOKE_BUDGET_MICRO_USD": bad}, tmp_path)
    with pytest.raises(ValueError, match="EI_SMOKE_TARGET_WORDS is a whole number"):
        LiveSettings.from_environment({**LIVE, "EI_SMOKE_TARGET_WORDS": bad or "0"}, tmp_path)


def test_live_settings_make_a_capped_brief_run_the_model_and_use_a_made_up_author(
    tmp_path: Path,
) -> None:
    settings = LiveSettings.from_environment(LIVE, tmp_path)
    assert settings.brief.budget_micro_usd == 3_000_000
    assert (settings.brief.idea, settings.brief.target_words) == (DEFAULT_IDEA, 1_200)
    assert settings.environment["EI_STAGE_EXECUTOR"] == "model"
    assert settings.environment["EI_STAGE_MODEL_PROFILE"] == "writer"
    assert settings.environment["OTHER"] == "kept"
    author = Path(settings.environment["EI_AUTHOR_PROFILE"])
    assert author.parent == tmp_path and "Smoke Test Author" in author.read_text(encoding="utf-8")
    assert settings.out == tmp_path / "out"


def test_live_settings_take_an_idea_a_target_and_a_folder_from_the_environment(
    tmp_path: Path,
) -> None:
    named = {
        **LIVE,
        "EI_SMOKE_IDEA": "How to brew tea",
        "EI_SMOKE_TARGET_WORDS": "800",
        "EI_SMOKE_OUT": str(tmp_path / "mine"),
        "EI_AUTHOR_PROFILE": "/a/real/person.toml",
    }
    settings = LiveSettings.from_environment(named, tmp_path / "scratch")
    assert (settings.brief.idea, settings.brief.target_words) == ("How to brew tea", 800)
    assert settings.out == tmp_path / "mine"
    assert settings.environment["EI_AUTHOR_PROFILE"] != "/a/real/person.toml"
