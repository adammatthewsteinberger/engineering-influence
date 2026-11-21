# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Every cassette committed under tests/cassettes loads and holds no secret."""

from pathlib import Path

from engineering_influence.infrastructure.cassettes.cassette_redactor import CassetteRedactor
from engineering_influence.infrastructure.cassettes.json_cassette_store import JsonCassetteStore

CASSETTES = Path(__file__).resolve().parents[1] / "cassettes"


def test_every_committed_cassette_loads_and_holds_no_secret() -> None:
    """None are committed yet. The first recording is a paid run that needs the maintainer's go-ahead."""
    store = JsonCassetteStore(CASSETTES, CassetteRedactor())
    for path in sorted(CASSETTES.glob("*.json")):
        assert store.load(path.stem).name == path.stem
