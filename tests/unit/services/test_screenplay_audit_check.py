# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ScreenplayAuditCheck: five sections, one verdict per source file in order, and every invention marked FILM."""

from engineering_influence.services.screenplay_audit_check import ScreenplayAuditCheck

VERDICTS = "## Source verdicts\n| Source | Verdict |\n|---|---|\n| 001 | carries the spine |\n| 002 | a side road |\n"
REST = (
    "## Internalization\n| Character | Wants | Fears |\n|---|---|---|\n| Mara | the hive | the dome |\n\n"
    "## Source to beat\n- Set-Up: 001\n\n"
    "## Compression\n- cuts the second drive; keeps the queen\n\n"
    "## Inventions\n- a night watchman, FILM\n"
)


def check(text: str) -> tuple[str, ...]:
    return ScreenplayAuditCheck().problems(text)


def test_a_complete_audit_has_no_problems() -> None:
    assert check(VERDICTS + REST) == ()


def test_a_missing_section_is_a_problem() -> None:
    assert "the audit needs a '## Compression' section" in check(
        VERDICTS + REST.split("## Compression")[0]
    )


def test_a_source_file_with_no_verdict_is_a_problem() -> None:
    gap = VERDICTS.replace("| 002 | a side road |\n", "| 003 | a side road |\n")
    assert any("001 to 002" in p for p in check(gap + REST))


def test_the_verdicts_must_be_in_order_without_repeats() -> None:
    repeated = VERDICTS.replace("| 002 |", "| 001 |")
    assert any("each once and in order" in p for p in check(repeated + REST))


def test_no_source_files_at_all_is_a_problem() -> None:
    empty = "## Source verdicts\n| Source | Verdict |\n|---|---|\n"
    assert "the source verdicts list no source files" in check(empty + REST)


def test_an_invention_not_marked_film_is_a_problem() -> None:
    text = VERDICTS + REST.replace("a night watchman, FILM", "a night watchman")
    assert "invention 'a night watchman' is not marked FILM" in check(text)


def test_a_missing_verdict_table_is_reported_without_checking_the_rest() -> None:
    assert "the audit needs a '## Source verdicts' section" in check(REST)
