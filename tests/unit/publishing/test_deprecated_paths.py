"""Old import paths keep working for one minor release and say where the class went."""

import importlib
import sys

import pytest

from engineering_influence.models.publishing.project_layout import ProjectLayout


def test_the_old_project_layout_path_still_works_and_warns() -> None:
    sys.modules.pop("engineering_influence.publishing.project_layout", None)

    with pytest.warns(DeprecationWarning, match="models.publishing.project_layout"):
        module = importlib.import_module("engineering_influence.publishing.project_layout")

    assert module.ProjectLayout is ProjectLayout
