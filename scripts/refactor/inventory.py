# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lists every class in the production tree with the facts the onion restructure needs."""

import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PACKAGE = "engineering_influence"
# Importing any of these means the module touches the outside world.
EFFECTFUL_MODULES = {
    "subprocess": "process",
    "shutil": "filesystem",
    "zipfile": "archive",
    "tempfile": "filesystem",
    "socket": "network",
    "urllib": "network",
    "httpx": "network",
    "PIL": "image",
    "pypdf": "pdf",
    "pdfplumber": "pdf",
    "reportlab": "pdf",
    "importlib.metadata": "entry-points",
    "sqlmodel": "database",
    "sqlalchemy": "database",
    "aio_pika": "broker",
    "fastapi": "transport",
    "mcp": "transport",
    "uvicorn": "transport",
}
# Calls on a path or a file that read or write it.
IO_CALLS = {
    "read_text",
    "write_text",
    "read_bytes",
    "write_bytes",
    "open",
    "mkdir",
    "unlink",
    "glob",
    "rglob",
    "iterdir",
    "exists",
    "is_file",
    "is_dir",
    "resolve",
}
EXCEPTION_BASES = {"Exception", "ValueError", "RuntimeError", "KeyError", "OSError"}


@dataclass
class ClassFacts:
    """One class and what its module imports and calls."""

    module: str
    name: str
    layer: str
    group: str
    kind: str
    bases: list[str]
    effects: list[str] = field(default_factory=list)
    uses_filesystem: bool = False
    methods: int = 0


class ClassInventory:
    """Walks the package once and reports a ClassFacts per class."""

    def __init__(self, root: Path) -> None:
        self._source = root / "src" / PACKAGE

    def run(self) -> list[ClassFacts]:
        """Every class, in module order; modules without a class are skipped."""
        facts: list[ClassFacts] = []
        for path in sorted(self._source.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            effects = self._effects(tree)
            uses_fs = self._uses_filesystem(tree)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    facts.append(self._facts(path, node, effects, uses_fs))
        return facts

    def _facts(
        self, path: Path, node: ast.ClassDef, effects: list[str], uses_fs: bool
    ) -> ClassFacts:
        relative = path.relative_to(self._source).with_suffix("")
        parts = relative.parts
        return ClassFacts(
            module=".".join((PACKAGE, *parts)),
            name=node.name,
            layer=parts[0],
            group=parts[1] if len(parts) > 2 else "",
            kind=self._kind(node),
            bases=[ast.unparse(base) for base in node.bases],
            effects=effects,
            uses_filesystem=uses_fs,
            methods=sum(isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) for n in node.body),
        )

    def _kind(self, node: ast.ClassDef) -> str:
        bases = {ast.unparse(base).split(".")[-1] for base in node.bases}
        decorators = {ast.unparse(d).split("(")[0].split(".")[-1] for d in node.decorator_list}
        if "Protocol" in bases or "ABC" in bases:
            return "interface"
        if bases & {"Enum", "StrEnum", "IntEnum", "Flag"}:
            return "enum"
        if bases & EXCEPTION_BASES or any(base.endswith("Error") for base in bases):
            return "exception"
        if "dataclass" in decorators:
            return "dataclass"
        if bases & {"BaseModel", "SQLModel"}:
            return "pydantic"
        if "NamedTuple" in bases or "TypedDict" in bases:
            return "record"
        return "plain"

    def _effects(self, tree: ast.AST) -> list[str]:
        found: set[str] = set()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                for prefix, effect in EFFECTFUL_MODULES.items():
                    if name == prefix or name.startswith(prefix + "."):
                        found.add(effect)
        return sorted(found)

    def _uses_filesystem(self, tree: ast.AST) -> bool:
        return any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in IO_CALLS
            for node in ast.walk(tree)
        )


def main(argv: list[str] | None = None) -> int:
    """Print the inventory as JSON."""
    root = Path(argv[0]) if argv else Path.cwd()
    print(json.dumps([asdict(f) for f in ClassInventory(root).run()], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
