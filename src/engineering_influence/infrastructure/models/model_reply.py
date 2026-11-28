# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading a successful model reply: the JSON object, or the error for a reply in another shape."""

from typing import Any

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_reply_interface import ModelReplyInterface


class ModelReply(ModelReplyInterface):
    """Shared by every model adapter; each names itself in the message, and classifies failures its own way."""

    @staticmethod
    def body(response: httpx.Response, label: str) -> dict[str, Any]:
        """The JSON object in the reply's body, or an unexpected-reply error when the body is not a JSON object."""
        try:
            data = response.json()
        except ValueError as error:
            raise ModelReply.unexpected(label, "body") from error
        if not isinstance(data, dict):
            raise ModelReply.unexpected(label, "body")
        return data

    @staticmethod
    def unexpected(label: str, what: str) -> ApplicationError:
        """The error for a model reply this adapter does not understand, which stops the stage as a bad upstream reply."""
        return ApplicationError(
            code="MODEL_RESPONSE_UNEXPECTED",
            message=f"{label} sent a {what} this adapter does not understand",
            http_status=502,
        )
