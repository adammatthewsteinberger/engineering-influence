# Made with ❤️ by Vibey.

"""docs/README.md lists every page in docs/, once, with an audience, an owner and a last-verified date."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
AUDIENCES = {"Author", "Operator", "Developer", "Integrator"}


def indexed() -> list[tuple[str, str, str, str]]:
    rows = re.findall(
        r"^\| (\w+) \| \[(\w+)\]\(\2\.md\) \| (\w[\w ]*) \| (\d{4}-\d{2}-\d{2}) \|$",
        (DOCS / "README.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return [(audience, name, owner, date) for audience, name, owner, date in rows]


def test_every_page_in_docs_is_listed_exactly_once() -> None:
    pages = sorted(p.stem for p in DOCS.glob("*.md") if p.stem != "README")
    listed = sorted(name for _, name, _, _ in indexed())
    assert listed == pages


def test_every_row_names_a_known_audience_an_owner_and_a_date() -> None:
    rows = indexed()
    assert rows and all(audience in AUDIENCES for audience, _, _, _ in rows)
    assert all(owner == "Maintainer" for _, _, owner, _ in rows)
