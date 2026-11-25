# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Grants: which stage may call which of a locked server's tools, and the rules that keep them honest."""

from typing import Any

import pytest

from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock

A = "a" * 64


def server(name: str = "files", **changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": name,
        "command": ("/usr/bin/server",),
        "files": (("/usr/bin/server", A),),
        "env": (),
        "server_name": "s",
        "server_version": "1",
        "tool_names": ("read", "write", "list"),
        "tools_hash": A,
    }
    return McpServerLock(**{**fields, **changes})


def test_a_server_with_no_grants_gives_no_stage_anything() -> None:
    locked = server()
    assert locked.grants == ()
    assert locked.granted("research") == () and locked.model_names("research") == ()


def test_a_grant_names_the_tools_a_stage_may_call_in_the_servers_own_words_and_the_models() -> None:
    locked = server(grants=(("research", ("list", "read")),))
    assert locked.granted("research") == ("list", "read")
    assert locked.model_names("research") == ("files__list", "files__read")
    assert locked.granted("outline") == () and locked.model_names("outline") == ()


def test_grants_are_sorted_by_stage_and_each_stage_once() -> None:
    assert server(grants=(("a", ("read",)), ("b", ("read",)))).grants[0][0] == "a"
    with pytest.raises(ValueError, match="sorted by stage, each once"):
        server(grants=(("b", ("read",)), ("a", ("read",))))
    with pytest.raises(ValueError, match="sorted by stage, each once"):
        server(grants=(("a", ("read",)), ("a", ("write",))))


def test_grants_are_a_tuple_of_pairs() -> None:
    with pytest.raises(TypeError, match="tuple of"):
        server(grants=[("research", ("read",))])


@pytest.mark.parametrize("stage", ["", "Research", "1research", "re-search", "re search"])
def test_a_stage_is_named_in_lowercase_letters_digits_and_underscores(stage: str) -> None:
    with pytest.raises(ValueError, match="names a stage in lowercase"):
        server(grants=((stage, ("read",)),))


def test_a_stage_with_underscores_and_digits_is_fine() -> None:
    assert server(grants=(("copy_edit_2", ("read",)),)).granted("copy_edit_2") == ("read",)


@pytest.mark.parametrize("tools", [(), ["read"], ("write", "read"), ("read", "read")])
def test_a_stages_tools_are_a_sorted_non_empty_tuple_each_once(tools: Any) -> None:
    with pytest.raises(ValueError, match="sorted, non-empty tuple, each once"):
        server(grants=(("research", tools),))


def test_a_tool_the_lock_does_not_list_cannot_be_granted() -> None:
    with pytest.raises(ValueError, match="'delete' is not one of the tools this lock lists"):
        server(grants=(("research", ("delete",)),))


def test_a_tool_that_cannot_be_offered_under_a_valid_name_cannot_be_granted() -> None:
    with pytest.raises(ValueError, match="cannot be offered under a name a model provider accepts"):
        server(tool_names=("read file",), grants=(("research", ("read file",)),))
    long = "x" * 60
    with pytest.raises(ValueError, match="cannot be offered"):
        server(tool_names=(long,), grants=(("research", (long,)),))


def test_with_grants_adds_to_what_a_stage_may_call_and_keeps_everything_sorted() -> None:
    first = server().with_grants("research", ("write",))
    second = first.with_grants("research", ("read", "write"))
    other = second.with_grants("outline", ("list",))
    assert first.granted("research") == ("write",)
    assert second.granted("research") == ("read", "write")
    assert [stage for stage, _ in other.grants] == ["outline", "research"]


def test_with_grants_refuses_what_the_model_would_refuse() -> None:
    with pytest.raises(ValueError, match="not one of the tools this lock lists"):
        server().with_grants("research", ("delete",))
    with pytest.raises(ValueError, match="names a stage"):
        server().with_grants("Bad Stage", ("read",))


def test_without_grants_takes_named_tools_back_and_drops_a_stage_left_with_none() -> None:
    locked = server(grants=(("research", ("list", "read", "write")),))
    assert locked.without_grants("research", ("read",)).granted("research") == ("list", "write")
    assert locked.without_grants("research", ("list", "read", "write")).grants == ()


def test_without_grants_naming_no_tool_takes_them_all_and_leaves_other_stages() -> None:
    locked = server(grants=(("outline", ("list",)), ("research", ("read", "write"))))
    cleared = locked.without_grants("research", ())
    assert cleared.grants == (("outline", ("list",)),)


def test_without_grants_for_a_tool_that_was_not_granted_changes_nothing() -> None:
    locked = server(grants=(("research", ("read",)),))
    assert locked.without_grants("research", ("write",)).granted("research") == ("read",)
    assert locked.without_grants("nobody", ("read",)).grants == locked.grants


# ----------------------------------------------------------------------------- the whole lock
def test_a_lock_lists_what_a_stage_may_call_across_servers_in_server_name_order() -> None:
    lock = ToolLock(
        (
            server("zed", grants=(("research", ("write",)),)),
            server("alpha", grants=(("outline", ("read",)), ("research", ("list", "read")))),
            server("mid"),
        )
    )
    assert lock.granted("research") == ("alpha__list", "alpha__read", "zed__write")
    assert lock.granted("outline") == ("alpha__read",)
    assert lock.granted("drafting") == () and ToolLock().granted("research") == ()
