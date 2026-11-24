"""The data contracts: the brief, the book config, the run summary and the job message are frozen as JSON Schema."""

from snapshot import Snapshot

from engineering_influence.contracts.book_config.v1.book_config_v1 import BookConfigV1
from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1


def test_the_brief_schema_is_frozen() -> None:
    Snapshot("brief_v1_schema").check(Snapshot.schema(BookBriefV1.model_json_schema()))


def test_the_book_config_schema_is_frozen() -> None:
    Snapshot("book_config_v1_schema").check(Snapshot.schema(BookConfigV1.model_json_schema()))


def test_the_run_summary_schema_is_frozen() -> None:
    Snapshot("run_summary_v1_schema").check(Snapshot.schema(RunSummaryV1.model_json_schema()))


def test_the_job_message_schema_is_frozen() -> None:
    Snapshot("job_message_v1_schema").check(Snapshot.schema(JobMessage.model_json_schema()))
