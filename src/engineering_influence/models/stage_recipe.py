# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one stage reads, which prompt it uses, and how much it may write."""

import re
from collections.abc import Collection
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.stage_recipe_interface import StageRecipeInterface
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class StageRecipe(StageRecipeInterface):
    """A stage's name, its prompt template, the earlier stages it reads and its output cap.

    A stage's answer is kept as ``<stage>.md``, so ``inputs`` names earlier stages and each one
    is read from that stage's file. An input is also the name of a blank in the template.
    ``tools`` are the only tools the stage may use; a stage that names none gets none.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")

    stage: str
    template: str
    inputs: tuple[str, ...]
    max_output_tokens: int
    tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the recipe's name, template, inputs and output cap when it is built."""
        for label, value in (("stage", self.stage), ("template", self.template)):
            if not self.NAME.fullmatch(value):
                raise ValueError(f"a recipe's {label} is lowercase letters, digits and underscores")
        if not isinstance(self.inputs, tuple):
            raise TypeError("a recipe's inputs are a tuple of stage names")
        if any(not self.NAME.fullmatch(name) for name in self.inputs):
            raise ValueError("a recipe's inputs are stage names")
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("a recipe reads each stage once")
        if self.stage in self.inputs:
            raise ValueError("a stage cannot read its own answer")
        if self.max_output_tokens <= 0:
            raise ValueError("a recipe needs a positive output cap")
        if not isinstance(self.tools, tuple):
            raise TypeError("a recipe's tools are a tuple of tool names")
        if any(not ToolDefinition.NAME.fullmatch(name) for name in self.tools):
            raise ValueError("a recipe's tools are tool names")
        if len(set(self.tools)) != len(self.tools):
            raise ValueError("a recipe names each tool once")

    def output_name(self) -> str:
        """The artifact this stage's answer is kept as."""
        return f"{self.stage}.md"

    def input_artifacts(self) -> dict[str, str]:
        """Each input's blank name, and the artifact it is read from."""
        return {name: f"{name}.md" for name in self.inputs}

    def missing(self, stored: Collection[str]) -> tuple[str, ...]:
        """The input artifacts that are not among the stored ones, in order."""
        return tuple(name for name in self.input_artifacts().values() if name not in stored)
