# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of one run input inside a brief."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from engineering_influence.contracts.brief.v1.interfaces.run_input_v1_interface import (
    RunInputV1Interface,
)
from engineering_influence.models.run_input import RunInput


class RunInputV1(RunInputV1Interface, BaseModel):
    """One block of text given to a run: a name, the text and where it came from.

    It is checked by the same rules as the model it becomes, so an input a run could not use is refused when the brief
    is read, not when the run starts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    text: str
    origin: Literal["pasted", "file"] = "pasted"

    @model_validator(mode="after")
    def _check(self) -> "RunInputV1":
        RunInput(self.name, self.text, self.origin)
        return self
