"""Rules of ADR 0006 that the tree does not satisfy yet, held at today's count.

A count may go down and must never go up. When a restructuring PR lowers a count, the test
fails until ratchet.json records the new number, so progress cannot be lost. The last PR of the
restructure sets every count to zero. To record an improvement run
``EI_UPDATE_RATCHET=1 uv run pytest tests/architecture/test_ratchets.py``.
"""

import json
import os
from pathlib import Path

import pytest
from architecture_metrics import ArchitectureMetrics

RATCHET = Path(__file__).with_name("ratchet.json")
ACTUAL = ArchitectureMetrics().all()


def baseline() -> dict[str, int]:
    return dict(json.loads(RATCHET.read_text(encoding="utf-8")))


def test_every_rule_has_a_baseline_and_no_baseline_is_stale() -> None:
    assert sorted(baseline()) == sorted(ACTUAL)


@pytest.mark.parametrize("rule", sorted(ACTUAL))
def test_a_rule_never_gets_worse_and_improvements_are_recorded(rule: str) -> None:
    allowed, actual = baseline()[rule], ACTUAL[rule]
    assert actual <= allowed, f"{rule}: {actual} violations, but the baseline allows {allowed}"
    if actual < allowed and os.environ.get("EI_UPDATE_RATCHET"):
        recorded = {**baseline(), rule: actual}
        RATCHET.write_text(json.dumps(recorded, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    assert actual == allowed, f"{rule} improved from {allowed} to {actual}: lower ratchet.json"
