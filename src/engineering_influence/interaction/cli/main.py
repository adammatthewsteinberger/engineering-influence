"""Minimal CLI entry point for the initial public skeleton."""

import argparse


class CliApplication:
    """Runs the transport-level CLI without owning domain behavior."""

    def run(self, argv: list[str] | None = None) -> int:
        """Parse the command line and return its process status."""
        parser = argparse.ArgumentParser(prog="ei")
        parser.add_argument("--version", action="version", version="engineering-influence 0.1.0a1")
        parser.parse_args(argv)
        return 0


def main() -> None:
    """Console-script shim."""
    raise SystemExit(CliApplication().run())
