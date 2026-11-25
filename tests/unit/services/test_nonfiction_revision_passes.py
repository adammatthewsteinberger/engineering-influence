# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NonfictionRevisionPasses: structure, then lines, then copy, each reading what the one before wrote."""

from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.revision_passes_interface import (
    RevisionPassesInterface,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.nonfiction_revision_passes import NonfictionRevisionPasses

PASSES = NonfictionRevisionPasses()


def test_it_is_a_set_of_revision_passes() -> None:
    assert isinstance(PASSES, RevisionPassesInterface)


def test_the_passes_are_structure_then_lines_then_copy_and_match_the_plan() -> None:
    assert [p.stage for p in PASSES.passes()] == ["revise_structure", "revise_lines", "copy_edit"]
    assert tuple(p.stage for p in PASSES.passes()) == NonfictionRecipes.REVISION_STAGES
    plan = NonfictionRecipes().plan().stages
    assert (
        plan[plan.index("draft") + 1 : plan.index("assemble")] == NonfictionRecipes.REVISION_STAGES
    )


def test_the_first_pass_reads_the_draft_and_each_next_reads_what_the_last_wrote() -> None:
    passes = PASSES.passes()
    assert passes[0].source == "chapter"
    assert [p.source for p in passes[1:]] == [p.output for p in passes[:-1]]
    assert PASSES.final() == passes[-1].output == "copy"
    assert len({p.output for p in passes}) == 3


def test_each_pass_edits_more_narrowly_and_may_change_the_length_less() -> None:
    spreads = [p.max_ratio - p.min_ratio for p in PASSES.passes()]
    assert spreads == sorted(spreads, reverse=True)
    assert [(p.min_ratio, p.max_ratio) for p in PASSES.passes()] == [
        (0.8, 1.2),
        (0.9, 1.1),
        (0.95, 1.05),
    ]


def test_every_blank_a_pass_fills_is_one_its_template_declares_untrusted() -> None:
    library = TomlPromptLibrary()
    for editing in PASSES.passes():
        template = library.get(editing.template)
        lengths = {"words", "floor", "ceiling"}
        assert template.untrusted == frozenset(editing.blanks) - lengths
        assert template.identifier() == f"{editing.template}@2"
