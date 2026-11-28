# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A session's selected servers are names, each at most once."""

import pytest

from engineering_influence.models.acp_session import AcpSession


def test_a_selected_server_name_must_be_a_valid_lock_name() -> None:
    with pytest.raises(ValueError):
        AcpSession("s", "/work", None, ("Not A Name",))


def test_a_session_selects_each_server_once() -> None:
    with pytest.raises(ValueError):
        AcpSession("s", "/work", None, ("docs", "docs"))


def test_a_session_may_select_valid_names() -> None:
    assert AcpSession("s", "/work", None, ("docs", "search-2")).servers == ("docs", "search-2")
