"""Measures how far the production tree is from the rules of ADR 0006."""

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "src" / "engineering_influence"
PACKAGE = "engineering_influence"

# Layers as the ADR names them, with the names that are being replaced.
LEGACY = {"domain": "models", "interaction": "interactions"}
LAYERS = {
    "errors",
    "models",
    "contracts",
    "interfaces",
    "services",
    "controllers",
    "repositories",
    "infrastructure",
    "interactions",
    "runtime",
}
# What each layer may import from this package (ADR 0006, table "Layers, innermost first").
ALLOWED = {
    "errors": set(),
    "models": {"errors"},
    "contracts": {"errors", "models"},
    "interfaces": {"interfaces"},
    "services": {"errors", "models", "contracts", "interfaces", "services"},
    "controllers": {"errors", "models", "contracts", "interfaces", "services", "controllers"},
    "repositories": {"errors", "models", "contracts", "interfaces", "repositories"},
    "infrastructure": {"errors", "models", "contracts", "interfaces", "infrastructure"},
    "interactions": {
        "errors",
        "models",
        "contracts",
        "interfaces",
        "controllers",
        "interactions",
    },
    "runtime": LAYERS,
}
# Layers that may import `services.interfaces` without importing concrete services.
ADAPTERS = {"controllers", "repositories", "infrastructure", "interactions"}
TYPE_ONLY = {"errors", "models", "contracts"}
EXEMPT_FOLDERS = {"interfaces", "assets", "__pycache__"}
STDLIB = set(sys.stdlib_module_names)


def load_script(name: str) -> ModuleType:
    """Import a module from scripts/refactor by path."""
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / "refactor" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ArchitectureMetrics:
    """Every number here is a count of violations; zero means the rule holds everywhere."""

    def __init__(self, source: Path = SOURCE) -> None:
        self._source = source
        self._files = sorted(p for p in source.rglob("*.py") if p.name != "__init__.py")

    def all(self) -> dict[str, int]:
        """Every metric by name."""
        return {
            "files_outside_the_ring": self.files_outside_the_ring(),
            "files_under_a_legacy_layer_name": self.files_under_a_legacy_layer_name(),
            "folders_without_an_interfaces_folder": self.folders_without_an_interfaces_folder(),
            "classes_without_an_interface": self.classes_without_an_interface(),
            "interface_files_not_paired_with_a_module": self.interface_files_not_paired(),
            "interface_modules_that_break_the_declaration_rules": self.interface_rule_breaks(),
            "models_importing_beyond_models_errors_and_the_standard_library": self.model_impurities(),
            "imports_that_cross_the_layer_matrix": self.matrix_crossings(),
        }

    def layer(self, path: Path) -> str:
        """The top-level folder a file lives in."""
        return path.relative_to(self._source).parts[0]

    def files_outside_the_ring(self) -> int:
        """Files in a folder that is not one of the ten layers (today: publishing/)."""
        return sum(
            len(p.relative_to(self._source).parts) > 1
            and self.layer(p) not in LAYERS
            and self.layer(p) not in LEGACY
            for p in self._files
        )

    def files_under_a_legacy_layer_name(self) -> int:
        """Files still in `domain/` or `interaction/`."""
        return sum(self.layer(p) in LEGACY for p in self._files)

    def folders_without_an_interfaces_folder(self) -> int:
        """Folders holding modules that have no `interfaces/` folder beside them."""
        folders = {p.parent for p in self._files if p.parent.name not in EXEMPT_FOLDERS}
        folders = {f for f in folders if f.name not in EXEMPT_FOLDERS}
        return sum(not (folder / "interfaces").is_dir() for folder in folders)

    def classes_without_an_interface(self) -> int:
        """Classes that neither inherit an `*Interface` nor, for an enum, have a paired protocol."""
        count = 0
        for path in self._files:
            if path.parent.name == "interfaces":
                continue
            for node in self._classes(path):
                if self._is_interface(node) or self._implements(path, node):
                    continue
                count += 1
        return count

    def interface_files_not_paired(self) -> int:
        """Interface files not named `<module>_interface.py`, or without their module beside them."""
        count = 0
        for path in self._files:
            if path.parent.name != "interfaces":
                continue
            stem = path.stem.removesuffix("_interface")
            named = path.stem.endswith("_interface")
            top_level = (
                self.layer(path) == "interfaces" and path.parent == self._source / "interfaces"
            )
            paired = top_level or (path.parent.parent / f"{stem}.py").exists()
            count += not (named and paired)
        return count

    def interface_rule_breaks(self) -> int:
        """Interface modules that declare fields, lack `__slots__ = ()`, or import beyond the rules."""
        return sum(
            self._breaks_declaration_rules(path)
            for path in self._files
            if path.parent.name == "interfaces"
        )

    def model_impurities(self) -> int:
        """Imports in models that are neither the standard library, `errors` nor other models."""
        count = 0
        for path in self._files:
            if self.layer(path) not in {"models", "domain"}:
                continue
            for module in self._runtime_imports(path):
                top = module.split(".")[0]
                if top == PACKAGE:
                    count += module.split(".")[1:2] not in (["errors"], ["models"], ["domain"])
                else:
                    count += top not in STDLIB and top != "__future__"
        return count

    def matrix_crossings(self) -> int:
        """Imports of this package that the layer table does not allow."""
        count = 0
        for path in self._files:
            layer = LEGACY.get(self.layer(path), self.layer(path))
            if layer not in ALLOWED:
                continue
            for module, type_only in self._package_imports(path):
                parts = module.split(".")[1:]
                if not parts:
                    continue
                target = LEGACY.get(parts[0], parts[0])
                if target == layer:
                    continue
                if layer == "interfaces" and type_only and target in TYPE_ONLY:
                    continue
                if target == "services" and "interfaces" in parts and layer in ADAPTERS:
                    continue
                count += target not in ALLOWED[layer]
        return count

    def _classes(self, path: Path) -> list[ast.ClassDef]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return [n for n in tree.body if isinstance(n, ast.ClassDef)]

    def _is_interface(self, node: ast.ClassDef) -> bool:
        bases = {ast.unparse(b).split(".")[-1] for b in node.bases}
        return bool(bases & {"ABC", "Protocol"}) or node.name.endswith(("Interface", "Port"))

    def _implements(self, path: Path, node: ast.ClassDef) -> bool:
        bases = {ast.unparse(b).split(".")[-1] for b in node.bases}
        if any(b.endswith("Interface") for b in bases):
            return True
        enum = bases & {"Enum", "StrEnum", "IntEnum", "Flag"}
        return bool(enum) and (path.parent / "interfaces" / f"{path.stem}_interface.py").exists()

    def _breaks_declaration_rules(self, path: Path) -> bool:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not self._declaration_ok(node):
                return True
        return any(self._bad_runtime_import(path, module) for module in self._runtime_imports(path))

    def _declaration_ok(self, node: ast.ClassDef) -> bool:
        bases = {ast.unparse(b).split(".")[-1] for b in node.bases}
        if "Protocol" in bases:
            return True
        slots = False
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                return False
            if isinstance(item, ast.Assign):
                names = [t.id for t in item.targets if isinstance(t, ast.Name)]
                slots = slots or names == ["__slots__"]
                if names != ["__slots__"]:
                    return False
        return slots

    def _bad_runtime_import(self, path: Path, module: str) -> bool:
        top = module.split(".")[0]
        if top == PACKAGE:
            return "interfaces" not in module.split(".")
        return top not in STDLIB and top != "__future__"

    def _runtime_imports(self, path: Path) -> list[str]:
        return [m for m, type_only in self._all_imports(path) if not type_only]

    def _package_imports(self, path: Path) -> list[tuple[str, bool]]:
        return [(m, t) for m, t in self._all_imports(path) if m.split(".")[0] == PACKAGE]

    def _all_imports(self, path: Path) -> list[tuple[str, bool]]:
        """(module, imported only under TYPE_CHECKING) for every import in a file."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        guarded: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
                guarded.update(id(child) for body in node.body for child in ast.walk(body))
        found: list[tuple[str, bool]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.append((node.module, id(node) in guarded))
            elif isinstance(node, ast.Import):
                found.extend((alias.name, id(node) in guarded) for alias in node.names)
        return found
