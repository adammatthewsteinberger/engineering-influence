# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``ei`` console script and ``python -m engineering_influence`` entry point."""

from engineering_influence.runtime.cli_runtime import CliRuntime


def main() -> None:
    """Console-script shim."""
    raise SystemExit(CliRuntime().build().run())
