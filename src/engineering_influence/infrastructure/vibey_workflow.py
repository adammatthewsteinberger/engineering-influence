"""Vibey-compatible workflow definition adapter."""

from typing import ClassVar

from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project
from engineering_influence.interfaces.workflow_port import WorkflowPort


class VibeyWorkflowAdapter(WorkflowPort):
    """Translate methodology stages into ordered queue job kinds."""

    _STAGE_JOBS: ClassVar[dict[PipelineStage, tuple[str, ...]]] = {
        PipelineStage.THESIS: ("thesis.p1", "thesis.p2", "thesis.p3"),
        PipelineStage.BOOK: (
            "book.p4",
            "book.p5.pass1",
            "book.p5.pass2",
            "book.p5.pass3",
            "book.p5.pass4",
            "book.p5.pass5",
            "book.p5.pass6",
        ),
        PipelineStage.NOVEL: ("novel.p6", "novel.p7"),
        PipelineStage.SCREENPLAY: ("screenplay.p8", "screenplay.p9"),
        PipelineStage.HUB: ("hub.p10", "hub.p11"),
        PipelineStage.SPOKES: ("spokes.p12", "spokes.p13"),
        PipelineStage.DISTRIBUTION: ("distribution.p14",),
        PipelineStage.PUBLISH: (
            "publish.audit",
            "publish.pdf",
            "publish.covers",
            "publish.epub",
            "publish.render_qa",
            "publish.release_readiness",
        ),
    }

    def define(self, project: Project) -> tuple[str, ...]:
        """Return the selected stages' jobs in project order."""
        jobs: list[str] = []
        for stage in project.stages:
            jobs.extend(self._STAGE_JOBS[stage])
        return tuple(jobs)
