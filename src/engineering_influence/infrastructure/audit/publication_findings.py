# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the errors and warnings out of a publication report, for the audit and for the build."""

from typing import Any

from engineering_influence.interfaces.publication_findings_interface import (
    PublicationFindingsInterface,
)


class PublicationFindings(PublicationFindingsInterface):
    """The manuscript audit's issues and the release check's findings, as ``code: message`` lines."""

    @staticmethod
    def errors(result: dict[str, Any]) -> tuple[str, ...]:
        audit = result["manuscript_audit"]
        found = [f"{issue['code']}: {issue['message']}" for issue in audit["issues"]]
        found += [
            f"{finding['code']}: {finding['message']}"
            for finding in result["release_readiness"]["findings"]
            if finding["severity"] == "error"
        ]
        return tuple(found)

    @staticmethod
    def warnings(result: dict[str, Any]) -> tuple[str, ...]:
        audit = result["manuscript_audit"]
        found = [f"{issue['code']}: {issue['message']}" for issue in audit["warnings"]]
        found += [
            f"{finding['code']}: {finding['message']}"
            for finding in result["release_readiness"]["findings"]
            if finding["severity"] != "error"
        ]
        return tuple(found)
