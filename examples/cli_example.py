"""CLI example: start the sample pipeline through the `ei` command."""

import subprocess
import sys

from _sample import SampleProject


def main() -> None:
    project = SampleProject().load()
    command = [
        sys.executable,
        "-c",
        "from engineering_influence.interaction.cli.main import main; main()",
        "pipeline",
        "start",
        "--slug",
        project["slug"],
        "--title",
        project["title"],
    ]
    for postulate in project["postulates"]:
        command += ["--postulate", postulate]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
