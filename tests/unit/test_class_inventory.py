"""The inventory that the restructure's move map is built from."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "refactor" / "inventory.py"
spec = importlib.util.spec_from_file_location("class_inventory", SCRIPT)
assert spec is not None and spec.loader is not None
MODULE = importlib.util.module_from_spec(spec)
sys.modules["class_inventory"] = MODULE
spec.loader.exec_module(MODULE)

SOURCES = {
    "models/value.py": "from dataclasses import dataclass\n\n@dataclass\nclass Value:\n    n: int\n",
    "models/colour.py": "from enum import Enum\n\nclass Colour(Enum):\n    RED = 1\n",
    "errors/broken.py": "class BrokenError(ValueError):\n    pass\n",
    "interfaces/thing_port.py": "from abc import ABC\n\nclass ThingPort(ABC):\n    pass\n",
    "infrastructure/tools/runner.py": (
        "import subprocess\n\nclass Runner:\n"
        "    def run(self):\n        return subprocess.run(['x'])\n"
    ),
    "services/reader.py": (
        "class Reader:\n    def read(self, path):\n        return path.read_text()\n"
    ),
    "services/__init__.py": "",
    "services/empty.py": "VALUE = 1\n",
}


@pytest.fixture
def facts(tmp_path: Path) -> dict[str, object]:
    for relative, text in SOURCES.items():
        path = tmp_path / "src" / "engineering_influence" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return {f.name: f for f in MODULE.ClassInventory(tmp_path).run()}


def test_each_class_is_listed_with_its_kind(facts: dict[str, object]) -> None:
    kinds = {name: f.kind for name, f in facts.items()}  # type: ignore[attr-defined]
    assert kinds == {
        "Value": "dataclass",
        "Colour": "enum",
        "BrokenError": "exception",
        "ThingPort": "interface",
        "Runner": "plain",
        "Reader": "plain",
    }


def test_the_layer_group_and_module_come_from_the_path(facts: dict[str, object]) -> None:
    runner = facts["Runner"]
    assert (runner.layer, runner.group) == ("infrastructure", "tools")  # type: ignore[attr-defined]
    assert runner.module == "engineering_influence.infrastructure.tools.runner"  # type: ignore[attr-defined]
    assert facts["Value"].group == ""  # type: ignore[attr-defined]


def test_effects_and_file_access_are_detected(facts: dict[str, object]) -> None:
    assert facts["Runner"].effects == ["process"]  # type: ignore[attr-defined]
    assert facts["Reader"].uses_filesystem and not facts["Reader"].effects  # type: ignore[attr-defined]
    assert facts["Runner"].methods == 1  # type: ignore[attr-defined]


def test_main_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "src" / "engineering_influence" / "errors" / "x.py"
    path.parent.mkdir(parents=True)
    path.write_text("class OneError(Exception):\n    pass\n", encoding="utf-8")
    assert MODULE.main([str(tmp_path)]) == 0
    assert '"OneError"' in capsys.readouterr().out
