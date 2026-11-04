"""Transport-neutral project controller."""

from engineering_influence.contracts.pipeline_response import PipelineResponse
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)
from engineering_influence.domain.governing_postulates import GoverningPostulates
from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)


class ProjectController(ProjectControllerInterface):
    """Maps a validated project request to the shared application service."""

    def __init__(self, start_pipeline: StartPipelineInterface) -> None:
        self._start_pipeline = start_pipeline

    def start(self, request: ProjectRequest) -> PipelineResponse:
        """Build a domain project and start its first pipeline stage."""
        project = Project(
            slug=request.slug,
            title=request.title,
            postulates=GoverningPostulates(request.postulates),
            stages=tuple(PipelineStage(stage) for stage in request.stages),
        )
        job_id = self._start_pipeline.start(project)
        return PipelineResponse(job_id=job_id, project_slug=project.slug)
