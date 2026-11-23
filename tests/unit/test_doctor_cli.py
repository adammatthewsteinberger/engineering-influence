# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""``ei doctor --models``: what it prints, what it exits with, and that it sends nothing by default."""

import argparse
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.doctor_cli import DoctorCli
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.services.interfaces.model_doctor_interface import (
    ModelDoctorInterface,
)
from engineering_influence.services.interfaces.search_doctor_interface import (
    SearchDoctorInterface,
)

KEY = "sk-test-SECRETSECRET"
CATALOG = """
[[model]]
provider = "local"
model = "m"
family = "f"
context_window = 1000
max_output_tokens = 100
usage_policy_url = "https://example.test/policy"

[[model.price]]
effective = "2026-01-01"
input = 0
output = 0
cache_read = 0
cache_write = 0
batch_discount_percent = 0
"""
LOCAL = """
[[profile]]
name = "local"
adapter = "openai_compatible"
provider = "local"
model = "m"
base_url = "{url}"
"""
KEYED = LOCAL + 'api_key_env = "EI_TEST_DOCTOR_KEY"\n'


def NO_SEARCH() -> SearchDoctorInterface:
    raise AssertionError("a models check never builds the search doctor")


class Doctor(ModelDoctorInterface):
    def __init__(self, findings: tuple[DoctorFinding, ...] = ()) -> None:
        self.findings = findings
        self.calls: list[tuple[Path, Path]] = []

    def check(self, catalog_path: Path, profiles_path: Path) -> tuple[DoctorFinding, ...]:
        self.calls.append((catalog_path, profiles_path))
        return self.findings


def arguments(**changes: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "models": True,
        "search": False,
        "query": None,
        "catalog": Path("c.toml"),
        "profiles": Path("p.toml"),
        "probe": False,
    }
    values.update(changes)
    return argparse.Namespace(**values)


def test_a_clean_report_prints_each_line_and_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    doctor = Doctor((DoctorFinding("a", "price", True, "ok"), DoctorFinding("a", "key", True, "k")))
    assert DoctorCli(lambda probe: doctor, NO_SEARCH, {}).run(arguments()) == 0
    assert capsys.readouterr().out == (
        "ok   a: price: ok\nok   a: key: k\nall 2 checks passed; sent: nothing\n"
    )
    assert doctor.calls == [(Path("c.toml"), Path("p.toml"))]


def test_a_failed_check_exits_1_and_counts_the_failures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    doctor = Doctor(
        (DoctorFinding("a", "price", True, "ok"), DoctorFinding("a", "key", False, "no"))
    )
    assert DoctorCli(lambda probe: doctor, NO_SEARCH, {}).run(arguments()) == 1
    out = capsys.readouterr().out
    assert "FAIL a: key: no" in out
    assert out.endswith("1 of 2 checks failed\n")


def test_the_probe_flag_is_passed_to_the_builder_and_named_in_the_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    asked: list[bool] = []

    def build(probe: bool) -> ModelDoctorInterface:
        asked.append(probe)
        return Doctor((DoctorFinding("a", "probe", True, "available"),))

    assert DoctorCli(build, NO_SEARCH, {}).run(arguments(probe=True)) == 0
    assert asked == [True]
    assert "sent: one model-list request per profile" in capsys.readouterr().out


def test_the_files_default_to_the_environment() -> None:
    doctor = Doctor()
    environment = {"EI_MODEL_CATALOG": "env-c.toml", "EI_MODEL_PROFILES": "env-p.toml"}
    DoctorCli(lambda probe: doctor, NO_SEARCH, environment).run(
        arguments(catalog=None, profiles=None)
    )
    assert doctor.calls == [(Path("env-c.toml"), Path("env-p.toml"))]


def test_a_flag_wins_over_the_environment() -> None:
    doctor = Doctor()
    environment = {"EI_MODEL_CATALOG": "env-c.toml", "EI_MODEL_PROFILES": "env-p.toml"}
    DoctorCli(lambda probe: doctor, NO_SEARCH, environment).run(
        arguments(catalog=Path("flag.toml"), profiles=None)
    )
    assert doctor.calls == [(Path("flag.toml"), Path("env-p.toml"))]


@pytest.mark.parametrize("missing", ["catalog", "profiles"])
def test_a_file_that_is_not_named_anywhere_exits_2(
    capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    code = DoctorCli(lambda probe: Doctor(), NO_SEARCH, {"EI_MODEL_CATALOG": "  "}).run(
        arguments(**{missing: None})
    )
    assert code == 2
    assert "EI_MODEL_CATALOG and EI_MODEL_PROFILES" in capsys.readouterr().err


def test_an_invalid_file_prints_one_line_and_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    def build(probe: bool) -> ModelDoctorInterface:
        raise ApplicationError("MODEL_PROFILE_INVALID", "profile #1 (x) is missing 'adapter'")

    assert DoctorCli(build, NO_SEARCH, {}).run(arguments()) == 2
    assert capsys.readouterr().err == "error: profile #1 (x) is missing 'adapter'\n"


def test_a_missing_extra_is_named_and_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    def build(probe: bool) -> ModelDoctorInterface:
        raise ImportError("no httpx", name="httpx")

    assert DoctorCli(build, NO_SEARCH, {}).run(arguments(probe=True)) == 1
    err = capsys.readouterr().err
    assert "doctor needs the runtime extra" in err
    assert "httpx is missing" in err


def test_doctor_without_models_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as caught:
        CliRuntime().build().run(["doctor"])
    assert caught.value.code == 2


class Server:
    def __init__(self, status: int, delay: float = 0.0) -> None:
        self.status = status
        self.delay = delay
        self.requests: list[tuple[str, str | None]] = []


@contextmanager
def serving(status: int, delay: float = 0.0) -> Iterator[tuple[str, Server]]:
    state = Server(status, delay)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.requests.append((self.path, self.headers.get("authorization")))
            time.sleep(state.delay)
            self.send_response(state.status)
            self.send_header("content-length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def files(tmp_path: Path, profiles: str) -> list[str]:
    (tmp_path / "catalog.toml").write_text(CATALOG, encoding="utf-8")
    (tmp_path / "profiles.toml").write_text(profiles, encoding="utf-8")
    return [
        "--catalog",
        str(tmp_path / "catalog.toml"),
        "--profiles",
        str(tmp_path / "profiles.toml"),
    ]


def run(*extra: str) -> int:
    return CliRuntime().build().run(["doctor", "--models", *extra])


def test_the_real_command_checks_a_local_profile_and_sends_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with serving(200) as (url, server):
        assert run(*files(tmp_path, LOCAL.format(url=url))) == 0
    out = capsys.readouterr().out
    assert "ok   local: key: none needed" in out
    assert out.endswith("all 2 checks passed; sent: nothing\n")
    assert server.requests == []


def test_the_real_command_fails_a_missing_key_and_never_prints_a_present_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments_ = files(tmp_path, KEYED.format(url="https://models.example.test"))
    monkeypatch.delenv("EI_TEST_DOCTOR_KEY", raising=False)
    assert run(*arguments_) == 1
    assert "FAIL local: key: EI_TEST_DOCTOR_KEY is not set" in capsys.readouterr().out
    monkeypatch.setenv("EI_TEST_DOCTOR_KEY", KEY)
    assert run(*arguments_) == 0
    captured = capsys.readouterr()
    assert "EI_TEST_DOCTOR_KEY is set" in captured.out
    assert KEY not in captured.out + captured.err


def test_the_real_command_reads_its_files_from_the_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    given = files(tmp_path, LOCAL.format(url="http://127.0.0.1:9"))
    monkeypatch.setenv("EI_MODEL_CATALOG", given[1])
    monkeypatch.setenv("EI_MODEL_PROFILES", given[3])
    assert run() == 0
    assert "all 2 checks passed" in capsys.readouterr().out


def test_the_real_command_reports_a_bad_file_and_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(*files(tmp_path, "[[profile]]\nname = 'x'\n")) == 2
    assert capsys.readouterr().err.startswith("error: profile #1 (x) is missing")


def test_probe_asks_the_real_server_once_for_its_model_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with serving(200) as (url, server):
        assert run(*files(tmp_path, LOCAL.format(url=url)), "--probe") == 0
    assert server.requests == [("/v1/models", None)]
    out = capsys.readouterr().out
    assert "ok   local: probe: available" in out
    assert out.endswith("sent: one model-list request per profile\n")


def test_probe_reports_a_server_that_refuses_the_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EI_TEST_DOCTOR_KEY", KEY)
    with serving(401) as (url, server):
        assert run(*files(tmp_path, KEYED.format(url=url)), "--probe") == 1
    assert server.requests == [("/v1/models", f"Bearer {KEY}")]
    captured = capsys.readouterr()
    assert "FAIL local: probe: authentication failed" in captured.out
    assert KEY not in captured.out + captured.err


def test_probe_reports_a_server_that_is_not_there(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with serving(200) as (url, _):
        closed = url
    assert run(*files(tmp_path, LOCAL.format(url=closed)), "--probe") == 1
    assert "could not be reached: ConnectError" in capsys.readouterr().out


def test_probe_gives_up_on_a_server_that_does_not_answer_in_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with serving(200, delay=2.0) as (url, _):
        runtime = CliRuntime(probe_timeout_seconds=0.3)
        code = runtime.build().run(
            ["doctor", "--models", *files(tmp_path, LOCAL.format(url=url)), "--probe"]
        )
    assert code == 1
    assert "could not be reached: ReadTimeout" in capsys.readouterr().out


# --------------------------------------------------------------------------- doctor --search
class SearchDoctorFake(SearchDoctorInterface):
    def __init__(self, findings: tuple[DoctorFinding, ...] = ()) -> None:
        self.findings = findings
        self.queries: list[str] = []

    def check(self, query: str) -> tuple[DoctorFinding, ...]:
        self.queries.append(query)
        return self.findings


def searching(**changes: object) -> argparse.Namespace:
    return arguments(models=False, search=True, **changes)


def never_models(probe: bool) -> ModelDoctorInterface:
    raise AssertionError("a search check never builds the model doctor")


GOOD = (DoctorFinding("searxng", "search", True, "5 links, the first from example.org"),)
BAD = (DoctorFinding("searxng", "search", False, "could not search: down"),)


def test_a_clean_search_check_prints_each_line_and_says_what_was_sent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = SearchDoctorFake(GOOD)
    assert DoctorCli(never_models, lambda: fake, {}).run(searching()) == 0
    assert capsys.readouterr().out == (
        "ok   searxng: search: 5 links, the first from example.org\n"
        "all 1 checks passed; sent: one search request per provider\n"
    )
    assert fake.queries == ["open source book publishing"]


def test_the_query_can_be_chosen() -> None:
    fake = SearchDoctorFake(GOOD)
    DoctorCli(never_models, lambda: fake, {}).run(searching(query="beekeeping manuals"))
    assert fake.queries == ["beekeeping manuals"]


def test_a_failed_search_check_exits_1_and_counts_the_failures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert DoctorCli(never_models, lambda: SearchDoctorFake(BAD + GOOD), {}).run(searching()) == 1
    assert "1 of 2 checks failed" in capsys.readouterr().out


def test_a_search_check_needs_no_model_files(capsys: pytest.CaptureFixture[str]) -> None:
    code = DoctorCli(never_models, lambda: SearchDoctorFake(GOOD), {}).run(
        searching(catalog=None, profiles=None)
    )
    assert code == 0
    capsys.readouterr()


def test_an_unusable_search_setting_prints_one_line_and_exits_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def build() -> SearchDoctorInterface:
        raise ApplicationError(
            "STAGE_SEARXNG_URL_INVALID", "EI_SEARXNG_URL is not usable: no host", 503
        )

    assert DoctorCli(never_models, build, {}).run(searching()) == 2
    assert capsys.readouterr().err == "error: EI_SEARXNG_URL is not usable: no host\n"


def test_a_missing_extra_is_named_for_the_search_check_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def build() -> SearchDoctorInterface:
        raise ImportError("no httpx", name="httpx")

    assert DoctorCli(never_models, build, {}).run(searching()) == 1
    assert "httpx is missing" in capsys.readouterr().err


def test_models_and_search_cannot_be_asked_for_together() -> None:
    with pytest.raises(SystemExit) as caught:
        CliRuntime().build().run(["doctor", "--models", "--search"])
    assert caught.value.code == 2


class SearxngServer:
    def __init__(self, status: int, body: bytes) -> None:
        self.status, self.body = status, body
        self.requests: list[str] = []


@contextmanager
def searxng(status: int = 200, body: bytes | None = None) -> Iterator[tuple[str, SearxngServer]]:
    reply = (
        body
        if body is not None
        else b'{"results": [{"url": "https://example.org/a", "title": "A"}, {"url": "https://example.net/b", "title": "B"}]}'
    )
    state = SearxngServer(status, reply)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.requests.append(self.path)
            self.send_response(state.status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def search(*extra: str) -> int:
    return CliRuntime().build().run(["doctor", "--search", *extra])


@pytest.fixture
def no_brave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)


def test_the_real_command_searches_a_real_searxng_once_and_reports_the_host(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with searxng() as (url, server):
        monkeypatch.setenv("EI_SEARXNG_URL", url)
        assert search() == 0
    out = capsys.readouterr().out
    assert "ok   searxng: search: 2 links, the first from example.org" in out
    assert "sent: one search request per provider" in out
    assert server.requests == ["/search?q=open+source+book+publishing&format=json"]


def test_the_real_command_sends_the_query_it_was_given(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with searxng() as (url, server):
        monkeypatch.setenv("EI_SEARXNG_URL", url)
        assert search("--query", "queen bees") == 0
    assert server.requests == ["/search?q=queen+bees&format=json"]
    capsys.readouterr()


def test_the_real_command_names_the_json_format_when_searxng_refuses(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with searxng(403, b"forbidden") as (url, _):
        monkeypatch.setenv("EI_SEARXNG_URL", url)
        assert search() == 1
    out = capsys.readouterr().out
    assert "FAIL searxng: search: SearXNG refused the request (403); is json listed" in out
    assert "1 of 1 checks failed" in out


def test_the_real_command_fails_an_instance_that_is_not_there(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_SEARXNG_URL", "http://127.0.0.1:1")
    assert search() == 1
    assert (
        "FAIL searxng: search: could not search: SearXNG could not be reached"
        in capsys.readouterr().out
    )


def test_the_real_command_fails_an_instance_that_finds_nothing(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with searxng(200, b'{"results": []}') as (url, _):
        monkeypatch.setenv("EI_SEARXNG_URL", url)
        assert search() == 1
    assert "it answered, but with no links for that query" in capsys.readouterr().out


def test_the_real_command_with_nothing_configured_fails_and_says_how_to_set_one_up(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("EI_SEARXNG_URL", raising=False)
    assert search() == 1
    assert "no web search is set up: set EI_SEARXNG_URL" in capsys.readouterr().out


def test_the_real_command_refuses_an_address_with_no_host_before_sending_anything(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_SEARXNG_URL", "not a url")
    assert search() == 2
    assert capsys.readouterr().err.startswith("error: EI_SEARXNG_URL is not usable: ")


@contextmanager
def brave(status: int = 200) -> Iterator[tuple[str, list[tuple[str, str | None]]]]:
    """A local Brave Search that answers every search with one link, and keeps the path and token it was sent."""
    seen: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append((self.path, self.headers.get("x-subscription-token")))
            body = b'{"web": {"results": [{"url": "https://brave.example/x", "title": "t"}]}}'
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def test_a_brave_key_adds_a_second_provider_checked_on_its_own_after_searxng(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "  brave-key-SECRET  ")
    with searxng() as (url, _), brave() as (brave_url, seen):
        monkeypatch.setenv("EI_SEARXNG_URL", url)
        code = CliRuntime(brave_base_url=brave_url).build().run(["doctor", "--search"])
    assert code == 0
    out = capsys.readouterr().out
    assert out.index("searxng: search") < out.index("brave: search")
    assert "brave: search: 1 links, the first from brave.example" in out
    assert seen == [
        ("/res/v1/web/search?q=open+source+book+publishing&count=5", "brave-key-SECRET")
    ]
    assert "SECRET" not in out


def test_a_brave_key_alone_is_checked_and_a_refused_key_fails_without_printing_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("EI_SEARXNG_URL", raising=False)
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key-SECRET")
    with brave(401) as (brave_url, _):
        code = CliRuntime(brave_base_url=brave_url).build().run(["doctor", "--search"])
    out = capsys.readouterr().out
    assert code == 1
    assert (
        "FAIL brave: search: its quota or key is used up: Brave Search refused the request (401)"
        in out
    )
    assert "SECRET" not in out


def test_a_blank_searxng_setting_counts_as_not_set(
    monkeypatch: pytest.MonkeyPatch, no_brave: None, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_SEARXNG_URL", "   ")
    assert search() == 1
    assert "no web search is set up" in capsys.readouterr().out


def test_an_address_with_no_host_is_an_unusable_setting_not_a_failed_search(
    monkeypatch: pytest.MonkeyPatch, no_brave: None
) -> None:
    monkeypatch.setenv("EI_SEARXNG_URL", "https://")
    with pytest.raises(ApplicationError) as error:
        CliRuntime()._search_doctor()
    assert (error.value.code, error.value.http_status) == ("STAGE_SEARXNG_URL_INVALID", 503)


def test_brave_is_found_at_its_real_address_unless_a_test_says_otherwise() -> None:
    import inspect

    default = inspect.signature(CliRuntime.__init__).parameters["brave_base_url"].default
    assert default == "https://api.search.brave.com"
