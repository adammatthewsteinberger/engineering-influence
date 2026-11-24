"""A novel's dashes are left as they are."""

from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)
from engineering_influence.services.interfaces.verbatim_dashes_interface import (
    VerbatimDashesInterface,
)
from engineering_influence.services.verbatim_dashes import VerbatimDashes

PROSE = "“Wait—” she said. 1990–1995 – and on."


def test_it_is_a_dash_rewriter_that_changes_nothing() -> None:
    assert isinstance(VerbatimDashes(), DashRewriterInterface | VerbatimDashesInterface)
    assert VerbatimDashes().rewrite(PROSE) == PROSE
    assert VerbatimDashes().rewrite("") == ""


def test_the_non_fiction_rewriter_would_have_changed_it() -> None:
    assert "—" not in DashRewriter().rewrite(PROSE)
