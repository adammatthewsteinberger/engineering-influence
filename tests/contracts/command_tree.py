"""Reads an argparse parser as plain data: every command, option, choice and default, and none of the help text."""

import argparse
from pathlib import Path
from typing import Any


class CommandTree:
    """What a person can type, as JSON: the part of the CLI that scripts depend on.

    Help text is left out (rewording it is not a change to the contract) and so are argparse's own class names,
    which differ between Python versions. What is kept is what a script can observe: the commands and their
    names, each option's flags, whether it is required, takes a value, may be repeated, its type, choices and
    default.
    """

    @classmethod
    def of(cls, parser: argparse.ArgumentParser) -> dict[str, Any]:
        """The parser and every parser below it."""
        arguments: list[dict[str, Any]] = []
        commands: dict[str, Any] = {}
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                commands = {name: cls.of(child) for name, child in sorted(action.choices.items())}
                continue
            if isinstance(action, argparse._HelpAction):
                continue
            arguments.append(cls._argument(action))
        document: dict[str, Any] = {"arguments": sorted(arguments, key=lambda item: item["name"])}
        if commands:
            document["commands"] = commands
        subparsers = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        if subparsers:
            document["command_required"] = bool(subparsers[0].required)
        return document

    @classmethod
    def _argument(cls, action: argparse.Action) -> dict[str, Any]:
        return {
            "name": action.option_strings[0] if action.option_strings else action.dest,
            "flags": list(action.option_strings),
            "dest": action.dest,
            "positional": not action.option_strings,
            "required": bool(action.required)
            if action.option_strings
            else action.nargs not in ("?", "*"),
            "takes_value": action.nargs != 0,
            "repeatable": isinstance(action, argparse._AppendAction),
            "nargs": action.nargs if isinstance(action.nargs, (str, int)) else None,
            "type": getattr(action.type, "__name__", None),
            "choices": sorted(map(str, action.choices)) if action.choices else None,
            "default": cls._plain(action.default),
        }

    @staticmethod
    def _plain(value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return [CommandTree._plain(item) for item in value]
        return "<not json>"
