# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a brief written as TOML, the same way for a file on the command line and a prompt over ACP."""

import tomllib

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.services.interfaces.brief_reader_interface import BriefReaderInterface


class BriefReader(BriefReaderInterface):
    """TOML that is not valid, and TOML that is not a brief, are refused with one line that names the source.

    The source is a file name for the command line and a description for a prompt. The brief contract decides
    what a brief is; this reader only parses and reports.
    """

    def read_text(self, text: str, source: str) -> BookBrief:
        """The brief, or an ApplicationError (BRIEF_INVALID) that names ``source`` and what is wrong."""
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ApplicationError(
                code="BRIEF_INVALID",
                message=f"{source} is not valid TOML: {error}",
                http_status=422,
            ) from error
        try:
            return BookBriefV1.model_validate(data).to_model()
        except ValueError as error:
            first = str(error).splitlines()[1:2] or [str(error)]
            raise ApplicationError(
                code="BRIEF_INVALID",
                message=f"{source} is not a brief: {first[0].strip()}",
                http_status=422,
            ) from error
