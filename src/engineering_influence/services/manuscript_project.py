# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the book a run assembled as the files of a project, for the stages that check or build it."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.interfaces.manuscript_project_interface import (
    ManuscriptProjectInterface,
)


class ManuscriptProject(ManuscriptProjectInterface):
    """The ``manuscript/`` artifacts the ``assemble`` stage wrote: the config under ``books/`` and the chapters under ``src/``.

    A run needs exactly one book config; any other number stops the stage with ``STAGE_INPUT_MISSING``.
    """

    PREFIX = "manuscript/"

    def __init__(self, artifacts: ArtifactStoreInterface) -> None:
        self._artifacts = artifacts

    async def load(self, run: BookRun) -> tuple[dict[str, bytes], str]:
        """The files of the project and the slug of its book."""
        names = await asyncio.to_thread(self._artifacts.names, run.run_id)
        stored = [name for name in names if name.startswith(self.PREFIX)]
        configs = [
            name
            for name in stored
            if name.startswith(f"{self.PREFIX}books/") and name.endswith(".toml")
        ]
        if len(configs) != 1:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=(
                    f"stage {run.stage!r} needs the one book config the assemble stage writes under "
                    f"{self.PREFIX}books/, and this run has {len(configs)}"
                ),
                http_status=409,
            )
        files: dict[str, bytes] = {}
        for name in stored:
            data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
            files[name.removeprefix(self.PREFIX)] = data or b""
        slug = configs[0].removeprefix(f"{self.PREFIX}books/").removesuffix(".toml")
        return files, slug
