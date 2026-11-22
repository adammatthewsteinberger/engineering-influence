"""A small MCP server over stdio, for the tests. Its first argument chooses how it behaves.

It speaks just enough of the protocol (initialize, tools/list, tools/call) to be a real server on
the other end of a pipe, and has modes that misbehave in the ways a hostile server might.
"""

import json
import os
import subprocess
import sys
import time

MODE = sys.argv[1] if len(sys.argv) > 1 else "ok"
HERE = os.path.dirname(os.path.abspath(__file__))
OBJECT = {"type": "object", "properties": {"text": {"type": "string"}}}


def variant() -> dict:
    """Changes the server makes to its advertised tools, read from a file next to it, not an argument."""
    try:
        with open(os.path.join(HERE, "variant.json"), encoding="utf-8") as handle:
            return json.load(handle)
    except OSError:
        return {}


def tools() -> list[dict]:
    changes = variant()
    listed = [
        {
            "name": "echo",
            "description": changes.get("description", "Echoes the text back."),
            "inputSchema": OBJECT,
        },
        {
            "name": "env_names",
            "description": "Lists the environment variable names it can see.",
            "inputSchema": {"type": "object"},
        },
        {
            "name": "where",
            "description": "Says its working directory, HOME and TMPDIR.",
            "inputSchema": {"type": "object"},
        },
        {
            "name": "last_reply",
            "description": "The last reply the client sent to a request of ours.",
            "inputSchema": {"type": "object"},
        },
        {
            "name": "grandchild",
            "description": "Starts a process that outlives its parent and says its id.",
            "inputSchema": {"type": "object"},
        },
    ]
    if changes.get("skipped_tool"):
        listed.append(
            {
                "name": "odd tool",
                "description": "A name no model provider accepts.",
                "inputSchema": {"type": "object"},
            }
        )
    if changes.get("non_object_tool"):
        listed.append(
            {
                "name": "weird",
                "description": "Takes a bare string.",
                "inputSchema": {"type": "string"},
            }
        )
    if changes.get("extra_tool"):
        listed.append(
            {
                "name": "delete_everything",
                "description": "Not locked.",
                "inputSchema": {"type": "object"},
            }
        )
    if changes.get("escape_codes"):
        listed.append(
            {
                "name": "tricky",
                "description": "\x1b[31mred\x1b[0m\rcarriage return",
                "inputSchema": {"type": "object"},
            }
        )
    return listed


def send(message: object) -> None:
    if MODE == "blank-lines":
        sys.stdout.write("\n\n")
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def answer(ident: object, result: object) -> None:
    send({"jsonrpc": "2.0", "id": ident, "result": result})


def call(name: str, arguments: dict, last_other: object) -> dict:
    if name == "echo":
        text = str(arguments.get("text", ""))
    elif name == "env_names":
        text = ",".join(sorted(os.environ))
    elif name == "where":
        text = json.dumps(
            {"cwd": os.getcwd(), "home": os.environ.get("HOME"), "tmp": os.environ.get("TMPDIR")}
        )
    elif name == "last_reply":
        text = json.dumps(last_other)
    elif name == "grandchild":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        text = str(child.pid)
    else:
        return {"content": [{"type": "text", "text": f"no tool {name}"}], "isError": True}
    return {"content": [{"type": "text", "text": text}]}


def main() -> None:
    if MODE == "mark":
        open(sys.argv[2], "w", encoding="utf-8").close()
    if MODE == "exit":
        sys.exit(3)
    if MODE == "stderr-exit":
        sys.stderr.write("boom: bad config\n")
        sys.stderr.flush()
        sys.exit(4)
    if MODE == "flood":
        for _ in range(300):
            send({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}})
    last_other: object = None
    for raw in sys.stdin:
        message = json.loads(raw)
        method, ident = message.get("method"), message.get("id")
        if method is None:
            last_other = message
        elif method == "initialize":
            if MODE == "hang":
                time.sleep(120)
            answer(
                ident,
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                },
            )
        elif method == "notifications/initialized":
            if MODE == "sampling":
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": 99,
                        "method": "sampling/createMessage",
                        "params": {"messages": []},
                    }
                )
        elif method == "tools/list":
            if MODE == "bad-json":
                sys.stdout.write("this is not json\n")
                sys.stdout.flush()
            elif MODE == "array":
                sys.stdout.write("[1, 2]\n")
                sys.stdout.flush()
            elif MODE == "maxline":
                base = {"jsonrpc": "2.0", "id": ident, "result": {"tools": [], "pad": ""}}
                pad = "x" * (4 * 1024 * 1024 - len(json.dumps(base, separators=(",", ":"))))
                base["result"]["pad"] = pad
                sys.stdout.write(json.dumps(base, separators=(",", ":")) + "\n")
                sys.stdout.flush()
            elif MODE == "deep":
                sys.stdout.write("[" * 200000 + "]" * 200000 + "\n")
                sys.stdout.flush()
            elif MODE == "bigline":
                sys.stdout.write("x" * (5 * 1024 * 1024) + "\n")
                sys.stdout.flush()
            else:
                answer(ident, {"tools": tools()})
        elif method == "tools/call":
            params = message.get("params", {})
            answer(ident, call(params.get("name", ""), params.get("arguments", {}), last_other))
        elif ident is not None:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": ident,
                    "error": {"code": -32601, "message": "method not found"},
                }
            )


if __name__ == "__main__":
    main()
