"""Tests for the project aggregate."""

import pytest

from engineering_influence.domain.governing_postulates import GoverningPostulates
from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project


def test_project_keeps_neutral_postulates_and_selected_stages() -> None:
    project = Project(
        slug="demo",
        title="Demo",
        postulates=GoverningPostulates(("Use evidence.",)),
        stages=(PipelineStage.THESIS, PipelineStage.PUBLISH),
    )
    assert project.postulates.statements == ("Use evidence.",)
    assert project.limits.prohibit_fabricated_evidence is True


def test_empty_postulates_are_rejected() -> None:
    with pytest.raises(ValueError, match="postulates"):
        GoverningPostulates(())
