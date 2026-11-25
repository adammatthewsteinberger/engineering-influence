# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""DashRewriter: no em or en dash is left, and no comma the writer chose is touched."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)

EM = chr(0x2014)
EN = chr(0x2013)
REWRITER = DashRewriter()


def test_it_is_a_dash_rewriter() -> None:
    assert isinstance(REWRITER, DashRewriterInterface)


@pytest.mark.parametrize(
    ("written", "rewritten"),
    [
        (f"slow {EM} and steady", "slow, and steady"),
        (f"slow{EM}and steady", "slow, and steady"),
        (f"slow {EN} and steady", "slow, and steady"),
        (f"in 1990{EN}1995 it rose", "in 1990-1995 it rose"),
        (f"{EM} said the bee", "said the bee"),
        (f"he stopped {EM}\nthen went on", "he stopped\nthen went on"),
        (f"a pause {EM}. Then", "a pause. Then"),
        (f"(an aside {EM})", "(an aside)"),
        (f"three {EM}{EM} four", "three, , four"),
        ("a comma, and another,\nthen more", "a comma, and another,\nthen more"),
        ("no dashes at all - just a hyphen", "no dashes at all - just a hyphen"),
    ],
)
def test_dashes_are_rewritten_and_everything_else_is_kept(written: str, rewritten: str) -> None:
    assert REWRITER.rewrite(written) == rewritten


@given(st.text())
def test_no_dash_is_ever_left(text: str) -> None:
    result = REWRITER.rewrite(text)
    assert EM not in result and EN not in result
