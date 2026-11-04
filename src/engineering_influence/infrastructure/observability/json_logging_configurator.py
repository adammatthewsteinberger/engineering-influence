# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Structured JSON logging with secret masking and correlation ids."""

import logging
import sys
from typing import TextIO

from vibey_bootstrap.logging.correlation import CorrelationFilter
from vibey_bootstrap.logging.jsonformatter import JsonLogFormatter
from vibey_bootstrap.logging.masking import register_secret_keys
from vibey_bootstrap.logging.noise import silence_noisy_loggers

_MARKER = "_engineering_influence_json"
_SECRET_FIELDS = ("x-api-key", "ei_api_keys", "webhook_secret", "signature", "secret")


class JsonLoggingConfigurator:
    """Replace the root handlers with one JSON handler; safe to call more than once."""

    def __init__(self, level: int | str = "INFO", stream: TextIO | None = None) -> None:
        self._level = level
        self._stream = stream

    def configure(self) -> None:
        """Install the handler.

        Masking is by field name, so a secret interpolated into a message string is
        not caught: pass values as ``extra`` fields, never in the message text.
        """
        root = logging.getLogger()
        for handler in list(root.handlers):
            if getattr(handler, _MARKER, False):
                root.removeHandler(handler)
        handler = logging.StreamHandler(self._stream or sys.stderr)
        handler.setFormatter(JsonLogFormatter())
        handler.addFilter(CorrelationFilter())
        setattr(handler, _MARKER, True)
        root.addHandler(handler)
        root.setLevel(self._level)
        register_secret_keys(*_SECRET_FIELDS)
        # The request middleware logs each request once; uvicorn's access log would repeat it.
        silence_noisy_loggers("uvicorn.access")
