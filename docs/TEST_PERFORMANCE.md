# Test and CI performance

The quality gate runs the whole suite with coverage, and the CI matrix repeats it per Python version. This page records
what the suite costs and how the gate got faster, so a slowdown shows up in review.

## Baseline (serial, measured on the maintainer's Apple Silicon Mac, 10 cores)

| Run | Wall time | Result |
|---|---|---|
| `pytest -q` (serial) | 393 s | 12,272 passed, 3 skipped |
| `pytest --cov --cov-branch --cov-fail-under=100` (serial, the gate) | about 415 s | 100% |

The slowest single tests take 24 to 25 seconds (the evaluation runtime's judge and failure tests) and the cover builder
takes 3 to 7 seconds each. Most of the time is spread across thousands of small tests, which is why parallel workers help.

## What changed

- `pytest-xdist` is in the test extra, and the CI test job runs `pytest --cov --cov-branch --cov-fail-under=100 -n auto`.
- With eight workers, the gate takes about 154 s (100% coverage, 12,272 passed), against about 415 s serially.
- Eleven publishing tests failed only under parallel runs, because pypdf 7 compares the `jbig2dec` path it found when its
  `filters` module was first imported with the default configuration. That module was imported lazily, which could happen
  inside a test that narrows `PATH`. `tests/conftest.py` now imports `pypdf.filters` before any test runs.

## Still to do

Sharding by test file or by marker, fixtures that reuse LaTeX and `kubectl` output across tests, caching of the uv
environment and the Docker layers, and path filters so docs-only changes skip the Python matrix. Each is measured before it
is adopted.
