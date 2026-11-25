# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The models of the tool lock: server info, tools and their digest, a locked server and the lock."""

import hashlib
import json
from typing import Any

import pytest

from engineering_influence.models.mcp_call_result import McpCallResult
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_lock import ToolLock

A, B = "a" * 64, "b" * 64
OBJECT = {"type": "object", "properties": {"path": {"type": "string"}}}


# ---------------------------------------------------------------------------- server info
def test_server_info_holds_what_the_server_said() -> None:
    info = McpServerInfo("files", "1.2.0", "2025-06-18")
    assert (info.name, info.version, info.protocol_version) == ("files", "1.2.0", "2025-06-18")


@pytest.mark.parametrize(
    ("fields", "label"),
    [
        (("", "1", "p"), "name"),
        (("  ", "1", "p"), "name"),
        ((None, "1", "p"), "name"),
        (("n", "", "p"), "version"),
        (("n", 3, "p"), "version"),
        (("n", "1", ""), "protocol version"),
    ],
)
def test_server_info_needs_all_three_as_text(fields: tuple[Any, ...], label: str) -> None:
    with pytest.raises(ValueError, match=f"a server reports its {label}"):
        McpServerInfo(*fields)


def test_a_call_result_is_text_and_a_flag() -> None:
    assert McpCallResult("hi", False).text == "hi"
    assert McpCallResult("", True).is_error
    with pytest.raises(TypeError, match="answers in text"):
        McpCallResult(5, False)  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- descriptor
def tool(
    name: str = "read", description: str = "Reads a file.", schema: Any = None
) -> McpToolDescriptor:
    return McpToolDescriptor(name, description, OBJECT if schema is None else schema)


@pytest.mark.parametrize("name", ["", "   ", None, 5])
def test_a_tool_has_a_name(name: Any) -> None:
    with pytest.raises(ValueError, match="has a name"):
        McpToolDescriptor(name, "d", OBJECT)


def test_a_tools_description_is_text_and_its_schema_is_plain_json_object() -> None:
    with pytest.raises(TypeError, match="description is text"):
        McpToolDescriptor("n", 5, OBJECT)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="input schema is a JSON object"):
        McpToolDescriptor("n", "d", [1])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="plain JSON"):
        McpToolDescriptor("n", "d", {"type": "object", "x": {1, 2}})


def test_the_model_sees_the_server_name_then_two_underscores_then_the_tool_name() -> None:
    assert tool("read").model_name("files") == "files__read"


@pytest.mark.parametrize(
    ("name", "schema", "expected"),
    [
        ("read", OBJECT, True),
        ("read-file_2", OBJECT, True),
        ("read file", OBJECT, False),
        ("read.file", OBJECT, False),
        ("é", OBJECT, False),
        ("x" * 57, OBJECT, True),
        ("x" * 58, OBJECT, False),
        ("read", {"type": "string"}, False),
        ("read", {"properties": {}}, False),
    ],
)
def test_a_tool_is_offerable_when_its_model_name_is_valid_and_it_takes_an_object(
    name: str, schema: dict[str, Any], expected: bool
) -> None:
    assert tool(name, schema=schema).offerable("files") is expected  # "files__" is 7 characters


def test_a_definition_carries_the_model_name_description_and_schema() -> None:
    definition = tool().definition("files")
    assert isinstance(definition, ToolDefinition)
    assert (definition.name, definition.description) == ("files__read", "Reads a file.")
    assert definition.parameters == OBJECT


@pytest.mark.parametrize("description", ["", "   \n"])
def test_a_tool_with_no_description_is_described_as_having_none(description: str) -> None:
    text = tool("read", description).definition("files").description
    assert text == "The read tool (its server gave no description)."


def test_the_canonical_form_is_plain_json_and_a_copy() -> None:
    descriptor = tool()
    canonical = descriptor.canonical()
    assert canonical == {"name": "read", "description": "Reads a file.", "input_schema": OBJECT}
    canonical["input_schema"]["properties"]["path"]["type"] = "changed"
    assert descriptor.input_schema["properties"]["path"]["type"] == "string"


# ------------------------------------------------------------------------------- tool set
def test_a_tool_set_is_a_tuple_of_distinct_names() -> None:
    with pytest.raises(TypeError, match="tuple of tools"):
        McpToolSet([tool()])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="each tool name once"):
        McpToolSet((tool("a"), tool("a", "other")))
    assert McpToolSet(()).names() == ()


def test_the_digest_is_the_sha256_of_the_canonical_tools_in_name_order() -> None:
    first, second = tool("alpha", "A"), tool("beta", "B")
    expected = hashlib.sha256(
        json.dumps(
            [first.canonical(), second.canonical()],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert McpToolSet((second, first)).digest() == McpToolSet((first, second)).digest() == expected


def test_a_digest_that_lock_files_depend_on_does_not_change() -> None:
    tools = McpToolSet((tool("alpha", "Does A."), tool("beta", "Does B. café")))
    assert tools.digest() == "2c98871fd60567752b0bc0fe7f22a2ad464d142ffc43546797bf25f1015cbdcf"


@pytest.mark.parametrize(
    "changed",
    [
        McpToolSet((tool("alpha", "Does A."),)),
        McpToolSet((tool("alpha", "Does A!"), tool("beta", "Does B."))),
        McpToolSet((tool("alpha2", "Does A."), tool("beta", "Does B."))),
        McpToolSet((tool("alpha", "Does A.", {"type": "object", "x": 1}), tool("beta", "Does B."))),
        McpToolSet((tool("alpha", "Does A."), tool("beta", "Does B."), tool("gamma", "C"))),
        McpToolSet(()),
    ],
)
def test_any_added_removed_renamed_or_reworded_tool_changes_the_digest(changed: McpToolSet) -> None:
    base = McpToolSet((tool("alpha", "Does A."), tool("beta", "Does B.")))
    assert changed.digest() != base.digest()


def test_names_offered_and_skipped_are_in_name_order() -> None:
    tools = McpToolSet(
        (
            tool("zeta"),
            tool("bad name"),
            tool("alpha"),
            tool("also bad"),
            tool("mid", schema={"type": "x"}),
        )
    )
    assert tools.names() == ("alpha", "also bad", "bad name", "mid", "zeta")
    assert [d.name for d in tools.offered("files")] == ["files__alpha", "files__zeta"]
    assert tools.skipped("files") == ("also bad", "bad name", "mid")


# --------------------------------------------------------------------------- server lock
def lock(**changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": "files",
        "command": ("/usr/bin/server", "/opt/server.js", "--flag"),
        "files": (("/opt/server.js", B), ("/usr/bin/server", A)),
        "env": ("FILES_ROOT",),
        "server_name": "files-server",
        "server_version": "1.2.0",
        "tool_names": ("read",),
        "tools_hash": A,
    }
    return McpServerLock(**{**fields, **changes})


def test_a_valid_lock_keeps_what_was_approved() -> None:
    server = lock()
    assert server.file_hashes() == {"/opt/server.js": B, "/usr/bin/server": A}
    assert (server.env, server.tool_names) == (("FILES_ROOT",), ("read",))


def test_a_lock_may_have_no_environment_and_no_tools() -> None:
    assert lock(env=(), tool_names=()).env == ()


@pytest.mark.parametrize("name", ["files", "a", "a1-b", "a" + "b" * 31])
def test_a_lock_name_is_lowercase_from_a_letter_up_to_32(name: str) -> None:
    assert lock(name=name).name == name


@pytest.mark.parametrize("name", ["", "Files", "1files", "-x", "a_b", "a b", "a.b", "a" + "b" * 32])
def test_other_lock_names_are_refused_because_double_underscore_separates_server_and_tool(
    name: str,
) -> None:
    with pytest.raises(ValueError, match="lock name is lowercase"):
        lock(name=name)


@pytest.mark.parametrize("command", [(), ["/usr/bin/server"]])
def test_a_command_is_a_non_empty_tuple(command: Any) -> None:
    with pytest.raises(ValueError, match="non-empty tuple"):
        lock(command=command)


@pytest.mark.parametrize("part", ["", 5, None])
def test_every_part_of_a_command_is_a_non_empty_string(part: Any) -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        lock(command=("/usr/bin/server", part))


@pytest.mark.parametrize("executable", ["server", "./server", "bin/server", "~/server"])
def test_a_command_starts_with_an_absolute_path(executable: str) -> None:
    with pytest.raises(ValueError, match="absolute path of its executable"):
        lock(command=(executable,))


@pytest.mark.parametrize(
    "launcher",
    ["npx", "pnpx", "bunx", "uvx", "pipx", "npm", "pnpm", "yarn", "docker", "podman", "env"],
)
def test_a_launcher_that_downloads_code_is_refused_whatever_directory_it_is_in(
    launcher: str,
) -> None:
    path = f"/usr/local/bin/{launcher}"
    with pytest.raises(ValueError, match=f"{launcher} fetches code that cannot be hashed"):
        lock(command=(path, "some-server"), files=((path, A),))


def test_a_server_that_merely_has_a_launcher_in_its_name_is_not_refused() -> None:
    path = "/opt/npx-like/server"
    assert lock(command=(path,), files=((path, A),)).command == (path,)


def test_files_are_a_sorted_tuple_of_absolute_paths_and_hashes_each_once() -> None:
    with pytest.raises(TypeError, match="tuple of"):
        lock(files=[("/usr/bin/server", A)])
    with pytest.raises(ValueError, match="sorted by path, each once"):
        lock(files=(("/usr/bin/server", A), ("/opt/server.js", B)))
    with pytest.raises(ValueError, match="sorted by path, each once"):
        lock(files=(("/usr/bin/server", A), ("/usr/bin/server", A)))
    with pytest.raises(ValueError, match="absolute path with a SHA-256"):
        lock(files=(("/usr/bin/server", A), ("opt/server.js", B)))
    with pytest.raises(ValueError, match="absolute path with a SHA-256"):
        lock(files=(("/opt/server.js", "B" * 64), ("/usr/bin/server", A)))
    with pytest.raises(ValueError, match="absolute path with a SHA-256"):
        lock(files=(("/opt/server.js", "b" * 63), ("/usr/bin/server", A)))


def test_the_executable_itself_must_be_locked() -> None:
    with pytest.raises(ValueError, match="executable itself is locked"):
        lock(files=(("/opt/server.js", B),))


@pytest.mark.parametrize(
    "env", [["X"], ("A", "A"), ("lower",), ("1A",), ("A-B",), ("",), ("A" * 65,)]
)
def test_environment_names_are_capitals_digits_and_underscores_each_once(env: Any) -> None:
    with pytest.raises(ValueError):
        lock(env=env)


def test_tool_names_are_a_tuple_of_distinct_non_empty_names() -> None:
    with pytest.raises(ValueError, match="tool_names is a tuple"):
        lock(tool_names=["read"])
    with pytest.raises(ValueError, match="tool_names is a tuple"):
        lock(tool_names=("read", "read"))
    with pytest.raises(ValueError, match="tool name is not empty"):
        lock(tool_names=("",))


@pytest.mark.parametrize("digest", ["", "A" * 64, "a" * 63, "a" * 65, "g" * 64])
def test_the_tools_hash_is_a_lowercase_sha256(digest: str) -> None:
    with pytest.raises(ValueError, match="tools hash is a SHA-256"):
        lock(tools_hash=digest)


@pytest.mark.parametrize("field", ["server_name", "server_version"])
def test_the_name_and_version_the_server_reported_are_recorded(field: str) -> None:
    with pytest.raises(ValueError, match="name and version the server reported"):
        lock(**{field: "  "})


# ----------------------------------------------------------------------------- tool lock
def test_a_tool_lock_finds_servers_by_name_and_lists_them_sorted() -> None:
    first, second = lock(name="zed"), lock(name="alpha")
    tool_lock = ToolLock((first, second))
    assert tool_lock.server("zed") is first
    assert tool_lock.server("nope") is None
    assert tool_lock.names() == ("alpha", "zed")
    assert ToolLock().servers == () and ToolLock().names() == ()
    assert ToolLock.VERSION == 1


def test_a_tool_lock_is_a_tuple_of_servers_with_distinct_names() -> None:
    with pytest.raises(TypeError, match="tuple of servers"):
        ToolLock([lock()])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="share a name"):
        ToolLock((lock(), lock()))
