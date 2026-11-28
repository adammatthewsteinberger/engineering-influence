# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A check that does not opt in is not repairable, and keeps the generic output code."""

from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)


class Plain(StageOutputCheckInterface):
    def check(self, stage: str, text: str, target_words: int | None) -> None:
        return None


def test_by_default_a_stage_is_not_repairable_and_keeps_the_generic_code() -> None:
    checks = Plain()
    assert checks.repairable("outline") is False
    assert checks.final_code("outline") == "STAGE_OUTPUT_INVALID"
