# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CanonFindingParser: only `ERROR` and `WARN` lines in the `where: [rule] message` shape are findings."""

from engineering_influence.models.canon_finding import CanonFinding
from engineering_influence.services.canon_finding_parser import CanonFindingParser


def test_error_and_warn_lines_are_findings_in_order() -> None:
    output = (
        "checking film 1\n"
        "ERROR scene 12: [wrong-date] the scene is set on a sol that does not exist\n"
        "WARN scene 40: [tone] the line reads as a lecture\n"
        "done\n"
    )
    assert CanonFindingParser().parse(output) == (
        CanonFinding(
            "ERROR", "scene 12", "wrong-date", "the scene is set on a sol that does not exist"
        ),
        CanonFinding("WARN", "scene 40", "tone", "the line reads as a lecture"),
    )


def test_a_line_in_any_other_shape_is_not_a_finding() -> None:
    output = "ERROR no rule here\nerror lower case: [rule] message\nINFO scene 1: [rule] message\n"
    assert CanonFindingParser().parse(output) == ()


def test_surrounding_space_on_a_finding_line_is_ignored() -> None:
    (finding,) = CanonFindingParser().parse("   ERROR scene 3: [rule] the message   \n")
    assert finding.message == "the message"


def test_a_finding_with_no_message_is_not_read() -> None:
    assert CanonFindingParser().parse("ERROR scene 3: [rule]\n") == ()
