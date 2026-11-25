# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""JsonCassetteStore: a strict, stable file format, and no secret kept or loaded."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.json_cassette_store import JsonCassetteStore
from engineering_influence.models.cassette import Cassette
from engineering_influence.models.cassette_interaction import CassetteInteraction

KEY = "sk-test-SECRETSECRET"


def interaction(**changes: Any) -> CassetteInteraction:
    values: dict[str, Any] = {
        "method": "POST",
        "path": "/v1/messages",
        "request_body": {"model": "m", "prompt": "Open chapter one."},
        "status": 200,
        "response_body": {"text": "A harbour at dawn."},
    }
    values.update(changes)
    return CassetteInteraction(**values)


def cassette(**changes: Any) -> Cassette:
    values: dict[str, Any] = {
        "name": "chapter-one",
        "provider": "anthropic",
        "interactions": (interaction(), interaction(status=429, response_body={"e": "slow"})),
        "note": "synthetic brief 'harbour'; model claude-test; recorded 2026-11-21",
    }
    values.update(changes)
    return Cassette(**values)


def make_store(root: Path) -> JsonCassetteStore:
    return JsonCassetteStore(root, CassetteRedactor([KEY]))


def valid() -> dict[str, Any]:
    return {
        "format": 1,
        "name": "chapter-one",
        "provider": "anthropic",
        "note": "n",
        "interactions": [
            {
                "request": {"method": "POST", "path": "/v1/messages", "body": {"a": 1}},
                "response": {"status": 200, "body": {"b": 2}},
            }
        ],
    }


def write(root: Path, data: Any, name: str = "chapter-one") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def refused(call: Any) -> str:
    with pytest.raises(ApplicationError) as error:
        call()
    assert error.value.code == "CASSETTE_INVALID"
    assert error.value.http_status == 500
    return error.value.message


def test_a_saved_cassette_loads_back_equal(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save(cassette())
    assert store.load("chapter-one") == cassette()


def test_the_file_is_written_the_same_way_every_time(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save(cassette())
    first = (tmp_path / "chapter-one.json").read_bytes()
    store.save(cassette())
    assert (tmp_path / "chapter-one.json").read_bytes() == first
    text = first.decode()
    assert text.endswith("}\n")
    assert '\n  "format": 1,\n  "interactions": [' in text
    assert list(json.loads(text)) == sorted(json.loads(text))


def test_saving_creates_missing_folders_and_leaves_no_partial_file(tmp_path: Path) -> None:
    root = tmp_path / "deep" / "cassettes"
    make_store(root).save(cassette())
    assert [path.name for path in root.iterdir()] == ["chapter-one.json"]


def test_saving_again_replaces_the_cassette(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save(cassette())
    store.save(cassette(note="second recording"))
    assert store.load("chapter-one").note == "second recording"


def test_text_that_is_not_ascii_is_kept_readable(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save(cassette(interactions=(interaction(response_body={"text": "caf\u00e9"}),)))
    assert "caf\u00e9" in (tmp_path / "chapter-one.json").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "changes",
    [
        {"interactions": (interaction(request_body={"p": f"use {KEY}"}),)},
        {"interactions": (interaction(response_body={"e": f"bad key {KEY}"}),)},
        {"interactions": (interaction(path=f"/v1/x?key={KEY}"),)},
        {"note": f"recorded with {KEY}"},
    ],
)
def test_a_cassette_holding_a_secret_is_refused_and_nothing_is_written(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    root = tmp_path / "cassettes"
    message = refused(lambda: make_store(root).save(cassette(**changes)))
    assert "looks like a secret" in message
    assert "nothing was written" in message
    assert KEY not in message
    assert not root.exists()


def test_a_cassette_with_a_secret_already_in_the_file_is_refused_on_load(tmp_path: Path) -> None:
    data = valid()
    data["interactions"][0]["response"]["body"] = {"echo": f"key {KEY}"}
    write(tmp_path, data)
    message = refused(lambda: make_store(tmp_path).load("chapter-one"))
    assert "looks like a secret" in message
    assert KEY not in message


def test_loading_refuses_a_name_that_is_not_a_cassette_name(tmp_path: Path) -> None:
    assert "not a cassette name" in refused(lambda: make_store(tmp_path).load("../outside"))


def test_loading_a_cassette_that_is_not_there_says_so(tmp_path: Path) -> None:
    assert "no cassette named 'gone'" in refused(lambda: make_store(tmp_path).load("gone"))


def test_loading_a_file_that_is_not_json_says_so(tmp_path: Path) -> None:
    (tmp_path / "chapter-one.json").write_text("{nope", encoding="utf-8")
    assert "not valid JSON" in refused(lambda: make_store(tmp_path).load("chapter-one"))


def broken(change: Any) -> dict[str, Any]:
    data = copy.deepcopy(valid())
    change(data)
    return data


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "not a JSON object"),
        (broken(lambda d: d.update(extra=1)), "unknown keys ['extra']"),
        (broken(lambda d: d.pop("format")), "not format 1"),
        (broken(lambda d: d.update(format=2)), "not format 1"),
        (broken(lambda d: d.update(name="other")), "names itself 'other'"),
        (broken(lambda d: d.pop("provider")), "missing 'provider'"),
        (broken(lambda d: d.pop("interactions")), "missing 'interactions'"),
        (broken(lambda d: d.update(interactions=[])), "at least one interaction"),
        (broken(lambda d: d.update(interactions=5)), "not iterable"),
        (broken(lambda d: d.update(interactions=["x"])), "only the keys"),
        (broken(lambda d: d["interactions"][0].update(extra=1)), "only the keys"),
        (broken(lambda d: d["interactions"][0].pop("request")), "missing 'request'"),
        (broken(lambda d: d["interactions"][0]["request"].update(extra=1)), "only the keys"),
        (broken(lambda d: d["interactions"][0]["request"].pop("method")), "missing 'method'"),
        (broken(lambda d: d["interactions"][0]["request"].pop("path")), "missing 'path'"),
        (broken(lambda d: d["interactions"][0]["response"].update(extra=1)), "only the keys"),
        (broken(lambda d: d["interactions"][0]["response"].pop("body")), "missing 'body'"),
        (broken(lambda d: d["interactions"][0]["response"].pop("status")), "missing 'status'"),
        (broken(lambda d: d["interactions"][0]["response"].update(status=700)), "between 100"),
        (broken(lambda d: d.update(provider=7)), "chapter-one"),
    ],
)
def test_a_file_that_breaks_the_format_is_refused_with_the_reason(
    tmp_path: Path, data: Any, message: str
) -> None:
    write(tmp_path, data)
    assert message in refused(lambda: make_store(tmp_path).load("chapter-one"))


def test_a_request_without_a_body_loads_as_none(tmp_path: Path) -> None:
    data = valid()
    del data["interactions"][0]["request"]["body"]
    write(tmp_path, data)
    assert make_store(tmp_path).load("chapter-one").interactions[0].request_body is None


def test_a_file_without_a_note_loads_with_an_empty_one(tmp_path: Path) -> None:
    data = valid()
    del data["note"]
    write(tmp_path, data)
    assert make_store(tmp_path).load("chapter-one").note == ""
