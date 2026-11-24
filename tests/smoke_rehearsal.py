"""The free rehearsal of a run: a scripted local model server, and the settings that point a run at it.

Shared by the unit tests (which give the build stage a scripted pass, because they have no TeX toolchain) and
the toolchain test (which builds the book for real). Nothing here talks to a live model.
"""

import json
import re
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from local_server import LocalServer, Reply, Seen
from smoke_run import SmokeRun

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
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


def rehearsal(
    tmp_path: Path,
    url: str,
    cap: int = 5_000_000,
    builder: ManuscriptBuilderInterface | None = None,
    settings: Mapping[str, str] | None = None,
) -> SmokeRun:
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
        **(settings or {}),
    }
    brief = BookBrief(kind=BookKind.NONFICTION, budget_micro_usd=cap, **BRIEF)  # type: ignore[arg-type]
    return SmokeRun(environment, NoSecrets(), brief, date(2026, 11, 22), builder=builder)
