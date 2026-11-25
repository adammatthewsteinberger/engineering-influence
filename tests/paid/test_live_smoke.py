# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A small book, end to end, against a real model. This spends money, so it runs only when told to.

    EI_ALLOW_PAID=1 EI_SMOKE_BUDGET_MICRO_USD=3000000 ... uv run pytest -m paid tests/paid

The settings are in docs/LIVE_SMOKE_TEST.md. The run is capped by ``EI_SMOKE_BUDGET_MICRO_USD`` (there is no default), the
report and every artifact are written to a folder so you can read them, and the folder is printed even when the run fails.
"""

import os
from pathlib import Path

import pytest
from smoke_run import LiveSettings, SmokeRun

from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider


@pytest.mark.paid
def test_a_small_book_runs_end_to_end_against_a_real_model(
    tmp_path_factory: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    scratch = tmp_path_factory.mktemp("smoke")
    try:
        settings = LiveSettings.from_environment(os.environ, scratch)
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)
    report = SmokeRun(settings.environment, EnvSecretProvider(), settings.brief).run()
    report.write(settings.out)
    with capsys.disabled():
        print(f"\nsmoke run {report.status}: spent {report.spent_micro_usd / 1_000_000:.4f} USD of")
        print(
            f"{report.cap_micro_usd / 1_000_000:.4f}; read the book and the report in {settings.out}"
        )
        for row in report.rows:
            print(
                f"  {row.stage:18} {row.outcome:10} {row.spent_micro_usd / 1_000_000:8.4f} USD  {row.seconds:6.1f}s"
            )
    assert report.completed, f"stopped at {report.stage}: {report.issues} (see {settings.out})"
    assert report.spent_micro_usd <= report.cap_micro_usd
    assert (settings.out / "manuscript").is_dir() and Path(settings.out / "audit.md").is_file()
