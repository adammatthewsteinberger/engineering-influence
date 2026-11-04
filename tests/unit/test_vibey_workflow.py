"""Workflow-definition adapter tests."""

from engineering_influence.domain.governing_postulates import GoverningPostulates
from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project
from engineering_influence.infrastructure import VibeyWorkflowAdapter


def test_workflow_contains_all_selected_methodology_jobs_in_order() -> None:
    project = Project(
        "demo",
        "Demo",
        GoverningPostulates(("Evidence first.",)),
        tuple(PipelineStage),
    )

    jobs = VibeyWorkflowAdapter().define(project)

    assert jobs[:3] == ("thesis.p1", "thesis.p2", "thesis.p3")
    assert jobs[3:10] == (
        "book.p4",
        "book.p5.pass1",
        "book.p5.pass2",
        "book.p5.pass3",
        "book.p5.pass4",
        "book.p5.pass5",
        "book.p5.pass6",
    )
    assert jobs[-6:] == (
        "publish.audit",
        "publish.pdf",
        "publish.covers",
        "publish.epub",
        "publish.render_qa",
        "publish.release_readiness",
    )
