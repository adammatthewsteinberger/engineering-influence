# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A placeholder phase runner that needs no model and no network."""

from engineering_influence.interfaces.runner_port import RunnerPort


class DeterministicRunner(RunnerPort):
    """Returns the same text for the same phase and project.

    This is the default so the whole stack runs offline and reproducibly. It does not
    write anything: a real LLM-backed runner implements the same port.
    """

    async def run(self, phase: str, context: dict[str, object]) -> str:
        """Return a short deterministic draft."""
        return f"{phase}: draft for {context.get('project_slug', 'project')}"
