"""Fitting a drafting call's context to a token budget, against a counter that counts words."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.models.assembled_context import AssembledContext
from engineering_influence.models.context_plan import ContextPlan
from engineering_influence.models.model_availability import ModelAvailability
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.model_response import ModelResponse
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.services.context_assembler import ContextAssembler


class WordCounter(ModelInterface):
    """Counts words, which makes every expected number checkable by hand; records each call."""

    def __init__(self) -> None:
        self.calls = 0

    def describe(self) -> ProviderDescriptor:
        raise NotImplementedError

    def availability(self) -> ModelAvailability:
        return ModelAvailability.AVAILABLE

    def count_tokens(self, request: ModelRequest) -> int:
        self.calls += 1
        return len((request.system + " " + request.prompt).split())

    def complete(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError


def words(text: str) -> int:
    return len(text.split())


def plan(**changes: object) -> ContextPlan:
    values: dict[str, object] = {
        "style": "Write plainly.",
        "grounding": "Mara is a diver.",
        "beats": "Mara dives.",
        "instruction": "Draft chapter three.",
    }
    values.update(changes)
    return ContextPlan(**values)  # type: ignore[arg-type]


def assembler(counter: WordCounter | None = None, tail: int = 4000) -> ContextAssembler:
    return ContextAssembler(counter or WordCounter(), "v1", max_tail_characters=tail)


# system "Write plainly." + "Mara is a diver." = 6 words; the prompt's beats section is
# "## Beats for this chapter / Mara dives." = 7 words and the instruction 3: base = 16.
BASE = 16
FOUR = ("One happens.", "Two happens.", "Three happens.", "Four happens.")
# "## Earlier chapters" is 3 words and each "- X happens." line is 3: all four add 15.
WITH_FOUR = BASE + 15
NOTE_WORDS = 8  # "(3 earlier chapter summaries left out to fit.)"


def test_everything_that_fits_is_kept() -> None:
    result = assembler().assemble(
        plan(prior_summaries=FOUR, previous_tail="First.\n\nSecond one."), 1000
    )
    assert (result.kept_summaries, result.omitted_summaries) == (4, 0)
    assert result.tail_characters == len("First.\n\nSecond one.")
    assert "left out" not in result.prompt
    assert result.prompt.index("One happens.") < result.prompt.index("Four happens.")


def test_the_measured_tokens_are_the_counters_figure_for_the_final_text() -> None:
    result = assembler().assemble(plan(prior_summaries=FOUR), 1000)
    assert result.input_tokens == WITH_FOUR == words(result.system + " " + result.prompt)


def test_all_summaries_fit_exactly_at_their_cost_and_not_one_token_under() -> None:
    fits = assembler().assemble(plan(prior_summaries=FOUR), WITH_FOUR)
    assert fits.kept_summaries == 4
    tighter = assembler().assemble(plan(prior_summaries=FOUR), WITH_FOUR - 1)
    assert tighter.kept_summaries < 4


def test_the_oldest_summaries_go_first_and_the_note_says_how_many() -> None:
    # One summary plus the note: base 16 + header 3 + one line 3 + note 8 = 30.
    result = assembler().assemble(plan(prior_summaries=FOUR), 30)
    assert (result.kept_summaries, result.omitted_summaries) == (1, 3)
    assert "Four happens." in result.prompt
    assert "One happens." not in result.prompt
    assert "(3 earlier chapter summaries left out to fit.)" in result.prompt


def test_keeping_all_can_fit_where_keeping_all_but_one_does_not() -> None:
    # Dropping one summary adds the 8-word note, so 3 kept costs 36 while all 4 cost 31.
    result = assembler().assemble(plan(prior_summaries=FOUR), 33)
    assert result.kept_summaries == 4


def test_a_tail_is_cut_from_its_start_to_a_paragraph_boundary() -> None:
    tail = "First para.\n\nSecond para here."
    # Full tail: base 16 + "## End of the previous chapter" 6 + 5 words = 27; 25 leaves 3 words.
    result = assembler().assemble(plan(previous_tail=tail), 25)
    assert result.tail_characters == len("Second para here.")
    assert result.prompt.count("Second para here.") == 1
    assert "First para." not in result.prompt


def test_a_paragraph_boundary_is_preferred_to_an_earlier_word_boundary() -> None:
    tail = "alpha beta gamma delta.\n\nepsilon zeta"
    # Room for four tail words: word-snapping alone would keep "gamma delta. epsilon zeta", but a
    # cut that reaches a paragraph break starts at the paragraph, so only the last one is kept.
    result = assembler().assemble(plan(previous_tail=tail), BASE + 6 + 4)
    assert result.tail_characters == len("epsilon zeta")


def test_a_tail_with_no_paragraph_break_starts_on_a_word() -> None:
    result = assembler().assemble(plan(previous_tail="alpha beta gamma delta"), BASE + 6 + 2)
    assert result.tail_characters == len("gamma delta")


class CharCounter(WordCounter):
    """Counts a token per four characters, so one long unbroken word is expensive."""

    def count_tokens(self, request: ModelRequest) -> int:
        return len(request.system + request.prompt) // 4


def test_a_tail_that_cannot_start_cleanly_is_left_out_even_with_room() -> None:
    counter = CharCounter()
    fixed = ContextAssembler(counter, "v1").assemble(plan(), 10_000).input_tokens
    result = ContextAssembler(counter, "v1").assemble(plan(previous_tail="x" * 400), fixed + 20)
    assert result.tail_characters == 0
    assert "End of the previous chapter" not in result.prompt


def test_when_no_summary_is_kept_no_summary_section_is_sent() -> None:
    result = assembler().assemble(plan(prior_summaries=FOUR), BASE)
    assert (result.kept_summaries, result.omitted_summaries) == (0, 4)
    assert "Earlier chapters" not in result.prompt
    assert "left out" not in result.prompt
    assert result.input_tokens == BASE


def test_no_room_means_no_tail_section() -> None:
    result = assembler().assemble(plan(previous_tail="Some earlier prose."), BASE)
    assert result.tail_characters == 0
    assert "End of the previous chapter" not in result.prompt


def test_the_tail_never_exceeds_its_character_limit() -> None:
    long_tail = "\n\n".join(f"Paragraph {i} here." for i in range(20))
    result = assembler(tail=60).assemble(plan(previous_tail=long_tail), 10_000)
    assert 0 < result.tail_characters <= 60
    assert long_tail.endswith(
        result.prompt.split("## End of the previous chapter\n")[1].split("\n\n##")[0]
    )


def test_a_zero_tail_limit_sends_no_tail() -> None:
    result = assembler(tail=0).assemble(plan(previous_tail="Some prose."), 10_000)
    assert result.tail_characters == 0


def test_summaries_are_fitted_before_the_tail() -> None:
    # Room for the base, all summaries and only a little tail: the summaries win.
    tail = "First para.\n\nSecond para here."
    result = assembler().assemble(plan(prior_summaries=FOUR, previous_tail=tail), WITH_FOUR + 9)
    assert result.kept_summaries == 4
    assert result.tail_characters == len("Second para here.")


def test_fixed_parts_that_do_not_fit_are_an_error_with_both_numbers() -> None:
    with pytest.raises(ApplicationError) as caught:
        assembler().assemble(plan(), BASE - 1)
    assert caught.value.code == "CONTEXT_TOO_LARGE"
    assert "need 16 input tokens" in caught.value.message
    assert "only 15 are available" in caught.value.message
    assert caught.value.http_status == 422
    assert assembler().assemble(plan(), BASE).input_tokens == BASE


def test_the_stable_prefix_is_the_system_text_and_does_not_change_between_calls() -> None:
    a = assembler().assemble(plan(), 1000)
    b = assembler().assemble(
        plan(beats="Different beats.", prior_summaries=FOUR, previous_tail="Prose here."), 1000
    )
    assert a.system == b.system == "Write plainly.\n\nMara is a diver."
    assert "Mara is a diver." not in a.prompt


def test_a_blank_grounding_is_left_out_of_the_system_text() -> None:
    assert assembler().assemble(plan(grounding="  "), 1000).system == "Write plainly."


def test_the_number_of_counting_calls_grows_slowly_with_the_book() -> None:
    counter = WordCounter()
    summaries = tuple(f"Chapter {i} happens." for i in range(200))
    tail = "\n\n".join(f"Paragraph {i} of prose." for i in range(300))
    assembler(counter).assemble(plan(prior_summaries=summaries, previous_tail=tail), 400)
    assert counter.calls < 40


def test_the_inputs_are_validated() -> None:
    for field in ("style", "beats", "instruction"):
        with pytest.raises(ValueError, match=field):
            plan(**{field: " "})
    with pytest.raises(ValueError, match="summary"):
        plan(prior_summaries=("fine", " "))
    with pytest.raises(ValueError, match="prompt version"):
        ContextAssembler(WordCounter(), " ")
    with pytest.raises(ValueError, match="tail limit"):
        ContextAssembler(WordCounter(), "v1", max_tail_characters=-1)
    with pytest.raises(ValueError, match="system and a prompt"):
        AssembledContext(" ", "p", 1, 0, 0, 0)
    with pytest.raises(ValueError, match="negative"):
        AssembledContext("s", "p", -1, 0, 0, 0)


@given(
    summaries=st.lists(st.text("abcdefg ", min_size=1, max_size=30).filter(str.strip), max_size=6),
    tail=st.text("abcdefg \n", max_size=200),
    budget=st.integers(BASE, BASE + 120),
    extra=st.integers(0, 30),
)
def test_more_budget_never_means_less_context(
    summaries: list[str], tail: str, budget: int, extra: int
) -> None:
    p = plan(prior_summaries=tuple(summaries), previous_tail=tail)
    small = assembler().assemble(p, budget)
    large = assembler().assemble(p, budget + extra)
    assert small.input_tokens <= budget
    assert large.input_tokens <= budget + extra
    assert large.kept_summaries >= small.kept_summaries
    if large.kept_summaries == small.kept_summaries:
        assert large.tail_characters >= small.tail_characters
