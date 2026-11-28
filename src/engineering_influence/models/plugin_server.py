# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A tool server a plugin names: a definition to review, never something that is run for you."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_server_interface import PluginServerInterface
from engineering_influence.models.mcp_command import McpCommand
from engineering_influence.models.mcp_endpoint_url import McpEndpointUrl
from engineering_influence.models.mcp_server_lock import McpServerLock


@dataclass(frozen=True, slots=True)
class PluginServer(PluginServerInterface):
    """What a plugin says about one MCP server: its name and either a command or an address.

    This is a **definition**, not an installation. Nothing is run or contacted because a plugin
    names a server: the command a person would type to lock it is *printed*, and the person runs
    ``ei tools add`` themselves, which is the step that starts the server (or contacts it) once and
    records what it is. A plugin names no grant, so a server it describes reaches no stage until a
    person runs ``ei tools grant``.

    The shape is checked by the same rules the tool lock uses (an absolute executable that is not a
    launcher, an https address with no secret in it, environment names in capitals), so a plugin
    cannot describe a server the lock would refuse. A command's parts must be printable text, so
    what is shown to a person is exactly what would be typed.
    """

    MAX_ARGS: ClassVar[int] = 64
    MAX_ARG_CHARS: ClassVar[int] = 1_000

    name: str
    command: tuple[str, ...] = ()
    env: tuple[str, ...] = ()
    url: str = ""
    bearer_env: str = ""

    def __post_init__(self) -> None:
        """Validate that the server names a command or an address."""
        if not isinstance(self.name, str) or not McpServerLock.NAME.fullmatch(self.name):
            raise ValueError("a server's name is lowercase letters, digits and hyphens, at most 32")
        if bool(self.command) == bool(self.url):
            raise ValueError(f"server {self.name!r} has a command or an address, and not both")
        if self.url:
            self._check_remote()
        else:
            self._check_local()

    def remote(self) -> bool:
        """Whether the server is reached at an address instead of started as a command."""
        return bool(self.url)

    def tools_add_arguments(self) -> tuple[str, ...]:
        """The arguments after ``ei`` that lock this server: what a person would type, and review."""
        if self.url:
            flags = ("--bearer-env", self.bearer_env) if self.bearer_env else ()
            return ("tools", "add", *flags, "--url", self.url, self.name)
        env_flags = tuple(part for variable in self.env for part in ("--env", variable))
        return ("tools", "add", *env_flags, self.name, "--", *self.command)

    def _check_remote(self) -> None:
        if self.env:
            raise ValueError(f"server {self.name!r} has an address, so it takes no env variables")
        McpEndpointUrl(self.url)
        if self.bearer_env and not McpServerLock.ENV.fullmatch(self.bearer_env):
            raise ValueError(f"server {self.name!r} has a bearer variable that is not a name")

    def _check_local(self) -> None:
        if self.bearer_env:
            raise ValueError(f"server {self.name!r} has a bearer variable but no address")
        McpCommand(self.command)
        if len(self.command) > self.MAX_ARGS:
            raise ValueError(f"server {self.name!r} has more than {self.MAX_ARGS} arguments")
        for part in self.command:
            if len(part) > self.MAX_ARG_CHARS or not part.isprintable():
                raise ValueError(
                    f"server {self.name!r} has an argument that is too long or not printable text"
                )
        if not isinstance(self.env, tuple) or len(set(self.env)) != len(self.env):
            raise ValueError(f"server {self.name!r} names each env variable once, in a tuple")
        if any(not McpServerLock.ENV.fullmatch(variable) for variable in self.env):
            raise ValueError(f"server {self.name!r} has an env name that is not capital letters")
