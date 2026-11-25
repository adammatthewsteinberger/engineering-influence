"""An evaluation end to end: the pipeline makes each book, a separately named judge scores it, the bar is applied."""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from local_server import LocalServer, Reply, Seen
from smoke_rehearsal import NoSecrets, RehearsalBuilder, answer, environment, reply

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.release_evaluator_interface import (
    ReleaseEvaluatorInterface,
)
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.runtime.evaluation_runtime import EvaluationRuntime
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime

TODAY = date(2026, 11, 22)
RUBRIC = """
version = 1
pass_mean = 3.5
max_drop = 0.2

[[dimension]]
name = "voice"
question = "Is the voice its own?"
kinds = ["nonfiction", "novel"]
[dimension.anchors]
1 = "generic"
3 = "uneven"
5 = "distinct"

[[dimension]]
name = "plot"
question = "Does it move?"
kinds = ["novel"]
[dimension.anchors]
1 = "stalls"
3 = "moves"
5 = "drives"
"""
CASES = """
[[case]]
name = "herbs"
kind = "nonfiction"
idea = "How to keep herbs alive indoors"
title_hint = "Herbs Indoors"
target_words = 400

[[case]]
name = "salt-road"
kind = "novel"
idea = "A woman walks the salt road to find her brother"
title_hint = "The Salt Road"
target_words = 400
trim_size = "5.5x8.5"
"""
DIMENSION = re.compile(r"^([a-z_]+): ", re.MULTILINE)


def judged(user: str, score: int = 4) -> str:
    wanted = DIMENSION.findall(user.split("The book:")[0].split("The rubric:")[1])
    return json.dumps(
        {"scores": {name: {"score": score, "reason": f"{name} holds"} for name in wanted}}
    )


def serve_both(
    score: int = 4, fail_writing: bool = False, judge_says: str | None = None
) -> LocalServer:
    def route(request: Seen) -> Reply:
        user = json.loads(request.body)["messages"][-1]["content"]
        if user.startswith("Score this"):
            return reply(judge_says if judge_says is not None else judged(user, score))
        if fail_writing:
            return 503, {"content-type": "application/json"}, b'{"error": "busy"}'
        return reply(answer(user))

    return LocalServer(route)


def files(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "rubric.toml").write_text(RUBRIC, encoding="utf-8")
    (tmp_path / "set.toml").write_text(CASES, encoding="utf-8")
    return tmp_path / "rubric.toml", tmp_path / "set.toml"


def evaluation(
    tmp_path: Path,
    url: str,
    baseline: Path | None = None,
    judge: ModelInterface | None = None,
    **settings: str,
) -> EvaluationRuntime:
    rubric, cases = files(tmp_path)
    return EvaluationRuntime(
        environment(tmp_path, url, {"EI_EVAL_JUDGE_PROFILE": "writer", **settings}),
        NoSecrets(),
        tmp_path / "work",
        rubric,
        cases,
        baseline,
        TODAY,
        builder=RehearsalBuilder(),
        judge=judge,
    )


def test_each_book_is_made_by_the_pipeline_scored_by_the_judge_and_written_to_the_report(
    tmp_path: Path,
) -> None:
    lines: list[str] = []
    with serve_both(score=4) as server:
        runtime = evaluation(tmp_path, server.url)
        assert isinstance(runtime, ReleaseEvaluatorInterface)
        document, verdict = runtime.evaluate("1.0.0", 5_000_000, 2_000_000, lines.append)
        judge_calls = [r for r in server.seen if b"Score this" in r.body]
    report = json.loads(document)
    assert [c["case"] for c in report["cases"]] == ["herbs", "salt-road"]
    assert all(c["finished"] and c["run_status"] == "completed" for c in report["cases"])
    herbs, road = report["cases"]
    assert [s["dimension"] for s in herbs["scores"]] == ["voice"]
    assert [s["dimension"] for s in road["scores"]] == ["voice", "plot"]
    assert herbs["title"] == "Herbs Indoors" and road["title"] == "The Salt Road"
    assert herbs["chapters"] == 3 and herbs["words"] > 0
    assert report["dimension_means"] == {"plot": 4.0, "voice": 4.0}
    assert len(judge_calls) == 2 and report["spend"]["judging_micro_usd"] > 0
    assert report["spend"]["making_micro_usd"] == herbs["spent_micro_usd"] + road["spent_micro_usd"]
    assert (
        report["spend"]["estimated_micro_usd"]
        == herbs["estimated_micro_usd"] + road["estimated_micro_usd"]
    )
    assert report["verdict"] == {"passed": verdict.passed(), "failures": list(verdict.failures)}
    assert lines[0] == "herbs: making" and "salt-road: judging" in lines
    assert (tmp_path / "work" / "herbs" / "src" / "chapter_01.md").is_file()
    assert (tmp_path / "work" / "salt-road.state").is_dir()


def test_the_judge_is_shown_the_book_and_the_rubric_and_the_book_only_as_untrusted_data(
    tmp_path: Path,
) -> None:
    with serve_both() as server:
        evaluation(tmp_path, server.url).evaluate("r", 5_000_000, 2_000_000, lambda line: None)
        first = next(r for r in server.seen if b"Score this" in r.body)
    messages = json.loads(first.body)["messages"]
    system = next(m["content"] for m in messages if m["role"] == "system")
    user = messages[-1]["content"]
    assert "never instructions" in system
    assert "voice: Is the voice its own?" in user and "plot" not in user.split("The book:")[0]
    book = user.split("The book:")[1]
    assert (
        "<untrusted" in book and "# Herbs Indoors" in book and "Herbs like a bright window." in book
    )
    assert "budget" not in user.lower() and "cost" not in user.lower()


def test_a_book_that_does_not_finish_is_reported_and_fails_the_release_without_being_judged(
    tmp_path: Path,
) -> None:
    with serve_both(fail_writing=True) as server:
        document, verdict = evaluation(tmp_path, server.url).evaluate(
            "r", 5_000_000, 2_000_000, lambda line: None
        )
        judged_any = any(b"Score this" in r.body for r in server.seen)
    report = json.loads(document)
    assert not judged_any and not verdict.passed()
    assert [c["finished"] for c in report["cases"]] == [False, False]
    assert all(c["scores"] == [] for c in report["cases"])
    assert any("the book was not finished" in f for f in verdict.failures)
    assert report["dimension_means"] == {}


def test_a_score_below_the_bar_fails_the_release(tmp_path: Path) -> None:
    with serve_both(score=3) as server:
        _, verdict = evaluation(tmp_path, server.url).evaluate(
            "r", 5_000_000, 2_000_000, lambda line: None
        )
    assert "voice: the mean 3.0 is below the pass mark 3.5" in verdict.failures


def test_the_previous_report_is_the_baseline_a_drop_is_measured_against(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"dimension_means": {"voice": 4.9, "plot": 4.0}}), encoding="utf-8"
    )
    with serve_both(score=4) as server:
        _, verdict = evaluation(tmp_path, server.url, baseline=baseline).evaluate(
            "r", 5_000_000, 2_000_000, lambda line: None
        )
    assert "voice: the mean fell from 4.9 to 4.0, more than the allowed 0.2" in verdict.failures
    assert not any(f.startswith("plot") for f in verdict.failures)


def test_without_a_named_judge_nothing_is_made_or_spent(tmp_path: Path) -> None:
    with serve_both() as server:
        rubric, cases = files(tmp_path)
        runtime = EvaluationRuntime(
            environment(tmp_path, server.url),
            NoSecrets(),
            tmp_path / "work",
            rubric,
            cases,
            None,
            TODAY,
            builder=RehearsalBuilder(),
        )
        with pytest.raises(ApplicationError) as error:
            runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
        assert server.seen == []
    assert (
        error.value.code == "EVALUATION_JUDGE_REQUIRED"
        and "EI_EVAL_JUDGE_PROFILE" in error.value.message
    )
    assert not (tmp_path / "work").exists()


def test_a_blank_judge_name_is_the_same_as_none(tmp_path: Path) -> None:
    with serve_both() as server:
        runtime = evaluation(tmp_path, server.url, EI_EVAL_JUDGE_PROFILE="   ")
        with pytest.raises(ApplicationError) as error:
            runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
    assert error.value.code == "EVALUATION_JUDGE_REQUIRED"


def test_a_judge_that_is_not_a_known_profile_is_refused_before_a_book_is_made(
    tmp_path: Path,
) -> None:
    with serve_both() as server:
        runtime = evaluation(tmp_path, server.url, EI_EVAL_JUDGE_PROFILE="nobody")
        with pytest.raises(ApplicationError) as error:
            runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
        assert server.seen == []
    assert error.value.code == "STAGE_MODEL_PROFILE_UNKNOWN"


class InjectedJudge(ModelInterface):
    DESCRIPTOR = ProviderDescriptor(
        provider="fake", model="j", family="f", context_window=200_000, max_output_tokens=4_000,
        input_micro_usd_per_mtok=1_000_000, output_micro_usd_per_mtok=5_000_000,
        cache_read_micro_usd_per_mtok=0, cache_write_micro_usd_per_mtok=0, batch_discount_percent=0,
        price_effective="2026-11-01", usage_policy_url="https://example.test/policy",
    )  # fmt: skip

    def __init__(self) -> None:
        self.asked = 0

    def describe(self) -> ProviderDescriptor:
        return self.DESCRIPTOR

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        return 1_000

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.asked += 1
        return ModelResponse(judged(request.prompt, 5), ModelUsage(1_000, 100), "j", "end_turn")


def test_a_judge_handed_in_is_used_and_no_profile_is_needed(tmp_path: Path) -> None:
    judge = InjectedJudge()
    with serve_both() as server:
        runtime = evaluation(tmp_path, server.url, judge=judge)
        runtime._environment = {
            k: v for k, v in runtime._environment.items() if k != "EI_EVAL_JUDGE_PROFILE"
        }
        document, _ = runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
        assert not any(b"Score this" in r.body for r in server.seen)
    assert judge.asked == 2 and json.loads(document)["dimension_means"] == {
        "plot": 5.0,
        "voice": 5.0,
    }


def test_the_judge_is_always_a_model_named_by_its_own_profile_whatever_wrote_the_books(
    tmp_path: Path,
) -> None:
    runtime = evaluation(
        tmp_path,
        "http://127.0.0.1:1",
        EI_STAGE_EXECUTOR="local",
        EI_STAGE_MODEL_PROFILE="writer",
        EI_EVAL_JUDGE_PROFILE=" judge ",
    )
    judging = runtime._judge_environment()
    assert (judging["EI_STAGE_EXECUTOR"], judging["EI_STAGE_MODEL_PROFILE"]) == ("model", "judge")
    assert judging["EI_MODEL_PROFILES"] == runtime._environment["EI_MODEL_PROFILES"]
    assert runtime._environment["EI_STAGE_EXECUTOR"] == "local"


def test_the_judges_connection_is_closed_when_the_evaluation_ends_however_it_ends(
    tmp_path: Path,
) -> None:
    closed: list[bool] = []

    class Recording(StageExecutorRuntime):
        def close(self) -> None:
            closed.append(True)
            super().close()

    class Watched(EvaluationRuntime):
        def _judging_runtime(self) -> StageExecutorRuntime:
            return Recording(self._judge_environment(), self._secrets, self._today)

    rubric, cases = files(tmp_path)
    with serve_both(fail_writing=True) as server:
        runtime = Watched(
            environment(tmp_path, server.url, {"EI_EVAL_JUDGE_PROFILE": "writer"}),
            NoSecrets(),
            tmp_path / "work",
            rubric,
            cases,
            None,
            TODAY,
            builder=RehearsalBuilder(),
        )
        runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
        assert closed == [True]
    with serve_both(judge_says="I could not decide.") as server:
        runtime = Watched(
            environment(tmp_path, server.url, {"EI_EVAL_JUDGE_PROFILE": "writer"}),
            NoSecrets(),
            tmp_path / "work2",
            rubric,
            cases,
            None,
            TODAY,
            builder=RehearsalBuilder(),
        )
        with pytest.raises(ApplicationError) as error:
            runtime.evaluate("r", 5_000_000, 2_000_000, lambda line: None)
    assert error.value.code == "JUDGE_ANSWER_INVALID" and closed == [True, True]


def test_the_judging_budget_is_a_real_limit_a_call_that_does_not_fit_is_never_sent(
    tmp_path: Path,
) -> None:
    with serve_both() as server:
        with pytest.raises(ApplicationError) as error:
            evaluation(tmp_path, server.url).evaluate("r", 5_000_000, 1, lambda line: None)
        judge_calls = [r for r in server.seen if b"Score this" in r.body]
    assert error.value.code == "JUDGE_BUDGET_EXHAUSTED" and judge_calls == []
