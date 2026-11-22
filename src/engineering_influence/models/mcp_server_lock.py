# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP server that has been reviewed and pinned."""

import re
from dataclasses import dataclass, replace
from typing import ClassVar

from engineering_influence.models.interfaces.mcp_server_lock_interface import (
    McpServerLockInterface,
)
from engineering_influence.models.mcp_command import McpCommand
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class McpServerLock(McpServerLockInterface):
    """What a person approved: the command, the files it runs, who the server said it was, and its tools.

    - ``command`` starts with an absolute path to the executable. ``files`` is the SHA-256 of that
      executable and of every file named in its arguments (the script it runs), so changed code is
      noticed before it is started. Installed dependencies are not covered, and neither is anything
      the script fetches or reads at run time.
    - The command is checked by ``McpCommand``: an absolute executable, and no launcher that
      downloads code on each run (``npx``, ``uvx``, ``docker``, ...), because what it would run
      cannot be hashed here.
    - ``server_name``, ``server_version`` and ``tools_hash`` are what the server reported and
      advertised when it was added. A server that later says or advertises anything else is not
      started. ``tool_names`` is the same list in words, so a refusal can say what changed.
    - ``env`` is the names of the variables the server is given. Their values come from the
      environment at run time and are never written to the lock.
    - ``grants`` say which stage may call which of the server's tools: for each stage, a sorted tuple
      of tool names, each one the lock lists and each one that can be offered to a model. A stage
      with no grant gets none of this server's tools, and there are no wildcards. A grant is a
      decision a person makes and reviews with the lock, never something inferred.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9-]{0,31}")
    HASH: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
    ENV: ClassVar[re.Pattern[str]] = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
    STAGE: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")

    name: str
    command: tuple[str, ...]
    files: tuple[tuple[str, str], ...]
    env: tuple[str, ...]
    server_name: str
    server_version: str
    tool_names: tuple[str, ...]
    tools_hash: str
    grants: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def __post_init__(self) -> None:
        if not self.NAME.fullmatch(self.name):
            raise ValueError(
                "a server's lock name is lowercase letters, digits and -, from a letter"
            )
        self._check_command()
        self._check_files()
        self._check_names()
        self._check_grants()
        if not self.HASH.fullmatch(self.tools_hash):
            raise ValueError("the tools hash is a SHA-256 in lowercase hex")
        if not self.server_name.strip() or not self.server_version.strip():
            raise ValueError("a lock records the name and version the server reported")

    def file_hashes(self) -> dict[str, str]:
        """The locked files and their SHA-256, by path."""
        return dict(self.files)

    def granted(self, stage: str) -> tuple[str, ...]:
        """The server's own names of the tools this stage may call; none if it has no grant."""
        return dict(self.grants).get(stage, ())

    def model_names(self, stage: str) -> tuple[str, ...]:
        """The names the model sees for the tools this stage may call, ``<server>__<tool>``."""
        return tuple(
            f"{self.name}{McpToolDescriptor.SEPARATOR}{tool}" for tool in self.granted(stage)
        )

    def with_grants(self, stage: str, tools: tuple[str, ...]) -> "McpServerLock":
        """This lock with the tools added to what the stage may call; the model checks the result."""
        merged = dict(self.grants)
        merged[stage] = tuple(sorted({*merged.get(stage, ()), *tools}))
        return replace(self, grants=tuple(sorted(merged.items())))

    def without_grants(self, stage: str, tools: tuple[str, ...]) -> "McpServerLock":
        """This lock with the tools taken from what the stage may call; none given takes them all."""
        merged = dict(self.grants)
        left = tuple(tool for tool in merged.get(stage, ()) if tools and tool not in tools)
        if left:
            merged[stage] = left
        else:
            merged.pop(stage, None)
        return replace(self, grants=tuple(sorted(merged.items())))

    def _check_command(self) -> None:
        McpCommand(self.command)

    def _check_files(self) -> None:
        if not isinstance(self.files, tuple):
            raise TypeError("files are a tuple of (path, hash) pairs")
        paths = [path for path, _ in self.files]
        if len(set(paths)) != len(paths) or paths != sorted(paths):
            raise ValueError("files are sorted by path, each once")
        if any(
            not path.startswith("/") or not self.HASH.fullmatch(digest)
            for path, digest in self.files
        ):
            raise ValueError("a locked file is an absolute path with a SHA-256 in lowercase hex")
        if self.command[0] not in paths:
            raise ValueError("the executable itself is locked")

    def _check_names(self) -> None:
        for label, names in (("env", self.env), ("tool_names", self.tool_names)):
            if not isinstance(names, tuple) or len(set(names)) != len(names):
                raise ValueError(f"{label} is a tuple of names, each once")
        if any(not self.ENV.fullmatch(name) for name in self.env):
            raise ValueError("an environment variable name is capital letters, digits and _")
        if any(not name for name in self.tool_names):
            raise ValueError("a tool name is not empty")

    def _check_grants(self) -> None:
        if not isinstance(self.grants, tuple):
            raise TypeError("grants are a tuple of (stage, tools) pairs")
        stages = [stage for stage, _ in self.grants]
        if len(set(stages)) != len(stages) or stages != sorted(stages):
            raise ValueError("grants are sorted by stage, each once")
        for stage, tools in self.grants:
            if not self.STAGE.fullmatch(stage):
                raise ValueError(
                    "a grant names a stage in lowercase letters, digits and underscores"
                )
            if not isinstance(tools, tuple) or not tools or tuple(sorted(set(tools))) != tools:
                raise ValueError("a stage's granted tools are a sorted, non-empty tuple, each once")
            for tool in tools:
                if tool not in self.tool_names:
                    raise ValueError(
                        f"{tool!r} is not one of the tools this lock lists, so it cannot be granted"
                    )
                if not ToolDefinition.NAME.fullmatch(
                    f"{self.name}{McpToolDescriptor.SEPARATOR}{tool}"
                ):
                    raise ValueError(
                        f"{tool!r} cannot be offered under a name a model provider accepts"
                    )
