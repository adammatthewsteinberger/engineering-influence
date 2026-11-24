"""The command line contract: every command and option of ``ei`` is frozen as a tree."""

from command_tree import CommandTree
from snapshot import Snapshot

from engineering_influence.runtime.cli_runtime import CliRuntime


def test_the_command_tree_is_frozen() -> None:
    Snapshot("cli_command_tree").check(CommandTree.of(CliRuntime().build().parser()))


def test_the_tree_leaves_out_help_text_so_rewording_a_help_line_changes_nothing() -> None:
    assert "help" not in Snapshot.render(CommandTree.of(CliRuntime().build().parser())).replace(
        '"--help"', ""
    )
