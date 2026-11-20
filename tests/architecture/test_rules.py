"""The rules of ADR 0006 hold everywhere in the tree, with no allowance for violations."""

import pytest
from architecture_metrics import ArchitectureMetrics

ACTUAL = ArchitectureMetrics().all()

RULES = [
    "classes_without_an_interface",
    "effectful_library_imports_in_models_contracts_and_services",
    "files_outside_the_ring",
    "files_under_a_legacy_layer_name",
    "folders_without_an_interfaces_folder",
    "imports_that_cross_the_layer_matrix",
    "interface_files_not_paired_with_a_module",
    "interface_modules_that_break_the_declaration_rules",
    "models_importing_beyond_models_errors_and_the_standard_library",
]


def test_no_rule_has_been_dropped_from_the_metrics() -> None:
    assert sorted(ACTUAL) == RULES


@pytest.mark.parametrize("rule", RULES)
def test_the_rule_holds_everywhere(rule: str) -> None:
    assert ACTUAL[rule] == 0, f"{rule}: {ACTUAL[rule]} violations"
