"""The text policy: what a novel may do that a non-fiction book may not."""

import pytest

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.typesetting.text_policy import TextPolicy


@pytest.mark.parametrize("name", [None, "nonfiction"])
def test_a_book_with_no_kind_or_a_nonfiction_kind_keeps_the_strict_house_style(
    name: str | None,
) -> None:
    policy = TextPolicy.for_name(name)
    assert policy.kind is BookKind.NONFICTION
    assert (policy.allows_em_dash, policy.keeps_scene_breaks, policy.allows_draft_in_dialogue) == (
        False,
        False,
        False,
    )


def test_a_novel_may_use_em_dashes_print_scene_breaks_and_quote_the_word_draft() -> None:
    policy = TextPolicy.for_name("novel")
    assert policy.kind is BookKind.NOVEL
    assert (policy.allows_em_dash, policy.keeps_scene_breaks, policy.allows_draft_in_dialogue) == (
        True,
        True,
        True,
    )


@pytest.mark.parametrize("name", ["novell", "", "Novel", "fiction", " novel"])
def test_an_unknown_kind_is_refused_with_the_valid_ones_named(name: str) -> None:
    with pytest.raises(ManuscriptError, match="'nonfiction' or 'novel'"):
        TextPolicy.for_name(name)
