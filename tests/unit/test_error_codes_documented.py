"""Every error code a person can meet is explained in the troubleshooting page, and the rest are named as internal."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "tests" / "contracts" / "snapshots" / "error_codes.json"
TROUBLESHOOTING = ROOT / "docs" / "TROUBLESHOOTING.md"

# The codes a person can see in a message from a command or an API response. Each has a row with its message.
USER_FACING = {
    "BRIEF_UNREADABLE",
    "CONTENT_LEVEL_NOT_ALLOWED",
    "EXPORT_TARGET_NOT_EMPTY",
    "CONTEXT_TOO_LARGE",
    "DATABASE_UNAVAILABLE",
    "EXPORT_NAME_CLASH",
    "LOCAL_SERVER_UNREACHABLE",
    "MODEL_REJECTED",
    "PATH_ESCAPE",
    "PRICING_REQUIRED",
    "RUN_HAS_NO_ARTIFACTS",
    "STAGE_MODEL_NOT_CONFIGURED",
    "STAGE_MODEL_PROFILE_UNKNOWN",
    "STAGE_MODEL_KEY_IN_CLEAR",
    "SCHEMA_OUT_OF_DATE",
    "TOOL_URL_REFUSED",
    "TOOL_ENV_MISSING",
    "WEBHOOK_TARGET_REJECTED",
    "SKILL_IMPORT_TOO_LARGE",
    "SOURCE_TOO_COMPLEX",
    "SOURCE_EMPTY",
    "SOURCE_FOLDER_MISSING",
    "SOURCE_TOO_LARGE",
    "STAGE_OUTPUT_INVALID",
    "SCREENPLAY_NO_TITLE",
    "SCREENPLAY_NO_SCENES",
    "SCREENPLAY_SCENE_INVALID",
    "SCENE_CARDS_UNREADABLE",
    "SCREENPLAY_NO_SOURCES",
    "SHOOTING_LOCK_UNREADABLE",
}


def codes() -> set[str]:
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return set(data if isinstance(data, list) else data.keys())


def test_every_user_facing_code_has_a_row_in_the_troubleshooting_table() -> None:
    text = TROUBLESHOOTING.read_text(encoding="utf-8")

    for code in sorted(USER_FACING):
        assert f"| `{code}` |" in text, f"docs/TROUBLESHOOTING.md has no row for {code}"


def test_every_user_facing_code_is_a_real_code_the_package_has() -> None:
    assert USER_FACING <= codes()


def test_the_user_facing_list_is_the_only_place_a_code_is_named_as_user_facing() -> None:
    documented = set(
        re.findall(r"^\| `([A-Z_]+)` \|", TROUBLESHOOTING.read_text(encoding="utf-8"), re.MULTILINE)
    )

    assert documented == USER_FACING, f"table and list disagree: {sorted(documented ^ USER_FACING)}"


def test_a_code_with_no_row_is_either_documented_somewhere_or_named_as_internal() -> None:
    docs = "".join(path.read_text(encoding="utf-8") for path in (ROOT / "docs").rglob("*.md")) + (
        ROOT / "README.md"
    ).read_text(encoding="utf-8")
    silent = (
        codes() - USER_FACING - set(INTERNAL) - {code for code in codes() if f"`{code}`" in docs}
    )

    assert not silent, (
        f"a new error code needs a row in the table, a mention in the docs, or a place in INTERNAL: {sorted(silent)}"
    )


# Codes that no person needs a row for: stage plumbing, job payloads, test cassettes, file formats. Each is named
# here so a new code cannot slip past without a decision.
INTERNAL = frozenset(
    {
        "AUTHOR_PROFILE_INVALID",
        "BRIEF_INVALID",
        "CASSETTE_MISMATCH",
        "CASSETTE_INVALID",
        "CASSETTE_UNRECORDABLE",
        "EVALUATION_BUDGET_INVALID",
        "EVALUATION_FILE_INVALID",
        "EVALUATION_OUT_NOT_EMPTY",
        "INVALID_JOB_PAYLOAD",
        "JUDGE_ANSWER_INVALID",
        "JUDGE_ANSWER_UNUSABLE",
        "JUDGE_INPUT_TOO_LARGE",
        "LOCAL_RUN_EXISTS",
        "LOCAL_RUN_MISSING",
        "MARKETPLACE_INVALID",
        "MCP_REPLY_INVALID",
        "MCP_SERVER_CLOSED",
        "MCP_SERVER_LIMIT",
        "MCP_SERVER_START_FAILED",
        "MCP_TOOL_ERROR",
        "METADATA_INVALID",
        "MODEL_CATALOG_INVALID",
        "MODEL_PROBE_FAILED",
        "MODEL_PROFILE_INVALID",
        "MODEL_RESPONSE_UNEXPECTED",
        "OUTLINE_INVALID",
        "PLUGIN_FOLDER_INVALID",
        "PLUGIN_IMPORT_EMPTY",
        "PLUGIN_IMPORT_INVALID",
        "PLUGIN_INDEX_INVALID",
        "PLUGIN_INVALID",
        "PLUGIN_LOCK_INVALID",
        "PROMPT_TEMPLATE_INVALID",
        "RUN_INPUT_INVALID",
        "SOURCES_NOT_STORED",
        "SKILL_FILE_EXISTS",
        "SKILL_FILE_UNUSABLE",
        "SKILL_IMPORT_INVALID",
        "SKILL_INVALID",
        "SKILL_LOCK_INVALID",
        "SKILL_MARKDOWN_INVALID",
        "SKILL_NOT_FOUND",
        "SKILL_SECTION_NOT_FOUND",
        "SKILL_SOURCE_INVALID",
        "SKILL_TARGET_EXISTS",
        "STAGE_EXECUTOR_UNKNOWN",
        "STAGE_HAS_NO_RECIPE",
        "STAGE_INPUT_MISSING",
        "STAGE_KIND_UNSUPPORTED",
        "STAGE_LOCAL_MODEL_INVALID",
        "STAGE_OUT_OF_ORDER",
        "STAGE_SEARXNG_URL_INVALID",
        "STAGE_TEMPLATE_MISMATCH",
        "STORY_BIBLE_INVALID",
        "TOOL_ENV_INVALID",
        "TOOL_LOCK_INVALID",
        "TOOL_REMOTE_NEEDS_EXTRA",
        "TOOL_SERVER_UNRESPONSIVE",
        "UNKNOWN_JOB_KIND",
        "UNKNOWN_STAGE",
        "MANUSCRIPT_TEXT_REFUSED",
        "BUNDLE_NEEDS_EXTRA",
    }
)
