# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Adds a server to the tool lock by running it once and recording what it says."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface
from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.models.mcp_command import McpCommand
from engineering_influence.models.mcp_endpoint_url import McpEndpointUrl
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_lock_addition import ToolLockAddition
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.interfaces.tool_lock_editor_interface import (
    ToolLockEditorInterface,
)


class ToolLockEditor(ToolLockEditorInterface):
    """Everything that can be refused is refused before the command is run.

    The name, the environment names, the command (an executable that exists, not a launcher), the
    files it names (each one readable, scripts given by absolute path) and a name already taken are
    all checked first, because adding a server **runs it**. Only then is it started once, under the
    probe's limits, and what it reports becomes the entry: the hashes of the executable and of every
    script among its arguments, its name and version, and a hash of its tools. A file named only
    inside an option (``--config=/x/y``) is not seen and not locked.
    """

    def __init__(
        self,
        probe: McpServerProbeInterface,
        hasher: FileHasherInterface,
        finder: ExecutableFinderInterface,
    ) -> None:
        """Remember the probe, the file hasher and the executable finder the lock edits use."""
        self._probe = probe
        self._hasher = hasher
        self._finder = finder

    def add(
        self,
        lock: ToolLock,
        name: str,
        argv: tuple[str, ...],
        env_names: tuple[str, ...],
        replace: bool,
    ) -> ToolLockAddition:
        """Run the server once, record what it is, and return the lock with it added."""
        self._vacant(lock, name, replace)
        bad = [env for env in env_names if not McpServerLock.ENV.fullmatch(env)]
        if bad or len(set(env_names)) != len(env_names):
            raise self._refused(
                "TOOL_ENV_INVALID", "environment names are capital letters, digits and _, each once"
            )
        command = self._command(argv)
        files = self._files(command)
        try:
            inspection = self._probe.inspect(command.argv, env_names)
        except TransientStageError as error:
            raise ApplicationError(
                code="TOOL_SERVER_UNRESPONSIVE", message=str(error), http_status=502
            ) from error
        try:
            server = McpServerLock(
                name=name,
                command=command.argv,
                files=files,
                env=env_names,
                server_name=inspection.info.name,
                server_version=inspection.info.version,
                tool_names=inspection.tools.names(),
                tools_hash=inspection.tools.digest(),
            )
            return ToolLockAddition(lock.with_server(server, replace), server, inspection)
        except ValueError as error:
            raise self._refused("TOOL_LOCK_INVALID", str(error)) from error

    def add_remote(
        self, lock: ToolLock, name: str, url: str, bearer_env: str, replace: bool
    ) -> ToolLockAddition:
        """Contact the server at the address once, record what it is, and return the lock with it added.

        The name, the address and the variable's name are all checked before anything is contacted.
        Only the address, the server's name and version and a hash of its tools can be recorded: there
        are no files to hash, and the server's code can change without the lock knowing.
        """
        self._vacant(lock, name, replace)
        try:
            McpEndpointUrl(url)
        except (ValueError, TypeError) as error:
            raise self._refused("TOOL_URL_REFUSED", str(error)) from error
        if bearer_env and not McpServerLock.ENV.fullmatch(bearer_env):
            raise self._refused(
                "TOOL_ENV_INVALID", "a bearer variable name is capital letters, digits and _"
            )
        try:
            inspection = self._probe.inspect_remote(url, bearer_env)
        except TransientStageError as error:
            raise ApplicationError(
                code="TOOL_SERVER_UNRESPONSIVE", message=str(error), http_status=502
            ) from error
        server = McpServerLock(
            name=name,
            command=(),
            files=(),
            env=(),
            server_name=inspection.info.name,
            server_version=inspection.info.version,
            tool_names=inspection.tools.names(),
            tools_hash=inspection.tools.digest(),
            url=url,
            bearer_env=bearer_env,
        )
        return ToolLockAddition(lock.with_server(server, replace), server, inspection)

    def grant(self, lock: ToolLock, name: str, stage: str, tools: tuple[str, ...]) -> ToolLock:
        """The lock with these tools of the server added to what the stage may call."""
        server = self._server(lock, name)
        if not tools:
            raise self._refused("TOOL_GRANT_INVALID", "name at least one tool to grant")
        try:
            return lock.with_server(server.with_grants(stage, tools), replace=True)
        except ValueError as error:
            raise self._refused("TOOL_GRANT_INVALID", str(error)) from error

    def revoke(self, lock: ToolLock, name: str, stage: str, tools: tuple[str, ...]) -> ToolLock:
        """The lock with these tools taken from the stage, or all of them if none are named."""
        server = self._server(lock, name)
        if not any(granted for granted_stage, granted in server.grants if granted_stage == stage):
            raise self._refused("TOOL_GRANT_UNKNOWN", f"stage {stage!r} has no grant from {name!r}")
        return lock.with_server(server.without_grants(stage, tools), replace=True)

    def _vacant(self, lock: ToolLock, name: str, replace: bool) -> None:
        if not McpServerLock.NAME.fullmatch(name):
            raise self._refused(
                "TOOL_NAME_INVALID",
                "a server's name is lowercase letters, digits and -, from a letter, up to 32 characters",
            )
        if lock.server(name) is not None and not replace:
            raise self._refused(
                "TOOL_LOCK_EXISTS",
                f"a server named {name!r} is already locked; use --replace to lock it again",
            )

    def _server(self, lock: ToolLock, name: str) -> McpServerLock:
        server = lock.server(name)
        if server is None:
            raise self._refused("TOOL_SERVER_UNKNOWN", f"no server named {name!r} is locked")
        return server

    def _command(self, argv: tuple[str, ...]) -> McpCommand:
        executable = self._finder.find(argv[0])
        if executable is None:
            raise self._refused(
                "TOOL_COMMAND_NOT_FOUND", f"{argv[0]!r} is not an executable file or on PATH"
            )
        try:
            return McpCommand((executable, *argv[1:]))
        except ValueError as error:
            raise self._refused("TOOL_COMMAND_REFUSED", str(error)) from error

    def _files(self, command: McpCommand) -> tuple[tuple[str, str], ...]:
        digests: dict[str, str] = {}
        for index, part in enumerate(command.argv):
            digest = self._hasher.digest(part)
            if digest is None:
                if index == 0:
                    raise self._refused("TOOL_FILE_UNREADABLE", f"{part} cannot be read as a file")
                continue
            if not part.startswith("/"):
                raise self._refused(
                    "TOOL_RELATIVE_SCRIPT",
                    f"give {part!r} as an absolute path, so it is the file that is locked",
                )
            digests[part] = digest
        return tuple(sorted(digests.items()))

    @staticmethod
    def _refused(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=422)
