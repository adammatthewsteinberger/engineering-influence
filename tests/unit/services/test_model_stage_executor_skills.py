# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A stage's prompt carries the skills enabled for it, versioned, and a skill can touch nothing else."""

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.guidance import Guidance
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.skill import Skill
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.no_output_checks import NoOutputChecks
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.read_skill_tool import ReadSkillTool
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner

CAP = 5_000_000
GUIDANCE = Guidance(
    "<installed_guidance>\nBe plain.\n</installed_guidance>", "skill_guidance@1:abc"
)


class Asker(AskModelInterface):
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        self.requests.append(request)
        return ModelAnswer("An answer.", True, (), 0, 1, False)


class Guidances(StageGuidanceInterface):
    """Gives its guidance to the named stages only, and remembers which stages were asked."""

    def __init__(self, guidance: Guidance, *stages: str) -> None:
        self.guidance = guidance
        self.stages = stages
        self.asked: list[str] = []

    def for_stage(self, stage: str) -> Guidance:
        self.asked.append(stage)
        return self.guidance if stage in self.stages else Guidance()


def request_for(
    stage: str, guidance: StageGuidanceInterface, registry: ToolRegistry | None = None
) -> ModelRequest:
    asker = Asker()
    store = InMemoryArtifactStore()
    for name in NonfictionRecipes().recipe(stage).input_artifacts().values():
        store.put("run-1", name, b"earlier text")
    registry = registry or ToolRegistry(())
    limits = ToolLoopLimits()
    executor = ModelStageExecutor(
        NonfictionRecipes(),
        TomlPromptLibrary(),
        store,
        RunToolLoop(asker, ToolRunner(registry, InMemoryJournal(), limits), limits),
        registry,
        LockToolGrants(ToolLock()),
        guidance,
        NoOutputChecks(),
        lambda budget: SpendGuard(budget),
    )
    run = BookRun(
        "run-1",
        BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
        NonfictionRecipes().plan(),
        Budget(cap=CAP),
        stage=stage,
    )
    asyncio.run(executor.execute(run, 1))
    return asker.requests[0]


def test_a_stage_with_no_guidance_sends_exactly_the_prompt_and_version_it_always_did() -> None:
    plain = request_for("brief", NoStageGuidance())
    assert plain.prompt_version == "stage_brief@2"
    assert "installed_guidance" not in plain.prompt and "installed_guidance" not in plain.system


def test_guidance_is_added_after_the_stages_own_prompt_and_the_version_names_it() -> None:
    plain = request_for("brief", NoStageGuidance())
    guided = request_for("brief", Guidances(GUIDANCE, "brief"))
    assert guided.prompt == f"{plain.prompt}\n\n{GUIDANCE.text}"
    assert guided.prompt_version == "stage_brief@2+skill_guidance@1:abc"


def test_guidance_never_reaches_the_system_prompt_the_cap_or_the_offered_tools() -> None:
    plain = request_for("outline", NoStageGuidance())
    guided = request_for("outline", Guidances(GUIDANCE, "outline"))
    assert guided.system == plain.system
    assert guided.max_output_tokens == plain.max_output_tokens
    assert guided.tools == plain.tools
    assert guided.tools == ()


def test_the_stage_being_run_is_the_stage_the_guidance_is_asked_about() -> None:
    guidance = Guidances(GUIDANCE, "outline")
    request_for("outline", guidance)
    assert guidance.asked == ["outline"]
    other = Guidances(GUIDANCE, "outline")
    request_for("positioning", other)
    assert other.asked == ["positioning"]


def test_guidance_for_another_stage_changes_nothing() -> None:
    plain = request_for("positioning", NoStageGuidance())
    other = request_for("positioning", Guidances(GUIDANCE, "outline"))
    assert other == plain


READING = Guidance(
    "<installed_guidance>\nRead.\n</installed_guidance>", "skill_guidance@2:abc", ("read_skill",)
)


def reading_registry() -> ToolRegistry:
    skill = Skill("research_methodology", 1, (), sections=(("Source Evaluation", "Use SIFT."),))
    return ToolRegistry((ReadSkillTool((skill,)),))


def test_guidance_that_asks_for_read_skill_offers_it_to_a_stage_that_had_no_tools() -> None:
    request = request_for("brief", Guidances(READING, "brief"), reading_registry())
    assert [tool.name for tool in request.tools] == ["read_skill"]


def test_it_is_not_offered_to_a_stage_the_guidance_does_not_cover() -> None:
    request = request_for("outline", Guidances(READING, "brief"), reading_registry())
    assert request.tools == ()


class Stub(ToolInterface):
    """A tool that does nothing, so a stage can be offered it by name."""

    def __init__(self, name: str) -> None:
        self._name = name

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            self._name,
            "A stub.",
            {"type": "object", "properties": {}, "additionalProperties": False},
        )

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        return ""


def test_a_guidance_tool_the_stage_already_has_is_not_offered_twice_and_the_order_is_kept() -> None:
    registry = ToolRegistry([Stub("web_search"), Stub("fetch_url"), Stub("read_skill")])
    asking = Guidance(
        "<installed_guidance>\nGo.\n</installed_guidance>", "id@1", ("fetch_url", "read_skill")
    )
    request = request_for("research", Guidances(asking, "research"), registry)
    assert [tool.name for tool in request.tools] == ["web_search", "fetch_url", "read_skill"]


def test_guidance_that_asks_for_a_tool_nobody_registered_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as error:
        request_for("brief", Guidances(READING, "brief"))
    assert (error.value.code, error.value.http_status) == ("STAGE_TOOL_UNKNOWN", 500)
