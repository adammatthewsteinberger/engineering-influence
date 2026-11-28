# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Assemble the documentation site's source from the repository's own Markdown.

The documents are written to read well on GitHub, with links between them relative to where they live in
the repository, and some links out of the ``docs`` folder to files that are not pages (the examples, the
source). ProperDocs builds a site from one folder, so this puts every page in one, renames it to a clean
URL, and rewrites each link so that it works on the site: a link to another page becomes a link between
the pages, and a link to anything else becomes a link to that file on GitHub. A link that goes nowhere
stops the build, so the site never publishes one.

    python scripts/build_docs_site.py --out .site-src
    properdocs build --strict

``properdocs.yml`` names ``.site-src`` as its documents folder and lists the pages in its ``nav``.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

REPOSITORY = "adammatthewsteinberger/engineering-influence"
GITHUB = f"https://github.com/{REPOSITORY}"

# Pages that live outside docs/, and the address each has on the site.
ROOT_PAGES = {
    "README.md": "index.md",
    "CONTRIBUTING.md": "contributing.md",
    "SECURITY.md": "security.md",
    "SUPPORT.md": "support.md",
    "CODE_OF_CONDUCT.md": "code-of-conduct.md",
    "CHANGELOG.md": "changelog.md",
}
# Files copied as they are, to the root of the site, where a crawler or a model looks for them.
ROOT_FILES = ("llms.txt", "llms-full.txt")
ADR_INDEX = "adr/index.md"
FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.DOTALL | re.MULTILINE)
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+\1")
LINK = re.compile(r"\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
SCHEME = re.compile(r"[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def staged_name(repo_path: str) -> str:
    """The address a repository Markdown file has on the site: lower case, hyphens, no underscores."""
    if repo_path in ROOT_PAGES:
        return ROOT_PAGES[repo_path]
    if repo_path.startswith("docs/adr/"):
        return "adr/" + posixpath.basename(repo_path)
    name = posixpath.basename(repo_path)
    return name.lower().replace("_", "-")


def pages(root: Path) -> dict[str, str]:
    """Every repository page that becomes a page of the site, mapped to its address there."""
    found = {path: staged for path, staged in ROOT_PAGES.items() if (root / path).is_file()}
    for path in sorted((root / "docs").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        found[relative] = staged_name(relative)
    for path in sorted((root / "docs" / "adr").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        found[relative] = staged_name(relative)
    return found


def anchor(fragment: str) -> str:
    """A GitHub heading anchor as Python-Markdown (ProperDocs) writes it: runs of hyphens become one."""
    return re.sub(r"-+", "-", fragment).strip("-")


def rewrite(
    text: str,
    source: str,
    staged: Mapping[str, str],
    kind: Callable[[str], str | None],
    branch: str,
) -> str:
    """Rewrite every link in ``text``, the body of the repository file ``source``, for the site.

    ``kind`` says whether a repository path is a ``"file"``, a ``"dir"`` or nothing. Code is left alone.
    """
    here = posixpath.dirname(staged[source])

    def resolve(address: str) -> str | None:
        """The repository path an address points at, or None when it leaves the repository."""
        if address.startswith(GITHUB + "/"):
            parts = address.removeprefix(GITHUB + "/").split("/", 2)
            if parts[0] in ("blob", "tree") and len(parts) == 3:
                return parts[2].rstrip("/")
            return None
        if SCHEME.match(address):
            return None
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(source), address))
        return None if joined.startswith("..") else joined

    def one(match: re.Match[str]) -> str:
        link, title = match.group(1), match.group(2)
        address, _, fragment = link.partition("#")
        if not address:
            return match.group(0)
        path = resolve(address)
        if path is None:
            return match.group(0)
        if path == "docs/adr":
            destination = ADR_INDEX
        elif path in staged:
            destination = staged[path]
        else:
            found = kind(path)
            if found is None:
                raise SystemExit(f"{source}: the link {link} goes nowhere")
            where = "tree" if found == "dir" else "blob"
            hash_ = f"#{fragment}" if fragment else ""
            return f"]({GITHUB}/{where}/{branch}/{path}{hash_}{title})"
        relative = posixpath.relpath(destination, here or ".")
        hash_ = f"#{anchor(fragment)}" if fragment else ""
        return f"]({relative}{hash_}{title})"

    def prose(chunk: str) -> str:
        pieces = []
        last = 0
        for span in CODE_SPAN.finditer(chunk):
            pieces.append(LINK.sub(one, chunk[last : span.start()]))
            pieces.append(span.group(0))
            last = span.end()
        pieces.append(LINK.sub(one, chunk[last:]))
        return "".join(pieces)

    out = []
    last = 0
    for block in FENCE.finditer(text):
        out.append(prose(text[last : block.start()]))
        out.append(block.group(0))
        last = block.end()
    out.append(prose(text[last:]))
    return "".join(out)


def adr_index(root: Path) -> str:
    """A page that lists the decision records, each with the status line it carries."""
    lines = ["# Architecture decision records", "", "| Record | Status |", "|---|---|"]
    for path in sorted((root / "docs" / "adr").glob("*.md")):
        text = path.read_text(encoding="utf-8").splitlines()
        title = text[0].removeprefix("# ").strip() if text else path.stem
        status = next(
            (line.removeprefix("Status:").strip() for line in text if line.startswith("Status:")),
            "",
        )
        lines.append(f"| [{title}]({path.name}) | {status} |")
    return "\n".join(lines) + "\n"


def theme_stylesheet() -> str:
    """The Vibey stylesheet from the locked ``vibey-engine`` package, or nothing when it is not installed."""
    try:
        import vibey_gh
    except ImportError:
        return ""
    css = Path(vibey_gh.__file__).parent / "templates" / "release" / "vibey.css"
    return css.read_text(encoding="utf-8") if css.is_file() else ""


def build(root: Path, out: Path, branch: str) -> list[str]:
    """Write the site's source under ``out`` and return the pages written, by their address."""
    if out.exists():
        shutil.rmtree(out)
    staged = pages(root)

    def kind(path: str) -> str | None:
        target = root / path
        return "dir" if target.is_dir() else "file" if target.is_file() else None

    for source, destination in staged.items():
        target = out / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (root / source).read_text(encoding="utf-8")
        target.write_text(rewrite(text, source, staged, kind, branch), encoding="utf-8")
    (out / ADR_INDEX).write_text(adr_index(root), encoding="utf-8")
    for name in ROOT_FILES:
        if (root / name).is_file():
            shutil.copyfile(root / name, out / name)
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: https://{REPOSITORY.split('/')[0]}.github.io/"
        f"{REPOSITORY.split('/')[1]}/sitemap.xml\n",
        encoding="utf-8",
    )
    css = out / "stylesheets"
    css.mkdir(parents=True, exist_ok=True)
    (css / "vibey.css").write_text(theme_stylesheet(), encoding="utf-8")
    (css / "site.css").write_text(
        (root / "docs-site" / "site.css").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return sorted([*staged.values(), ADR_INDEX])


def main(argv: list[str] | None = None) -> int:
    """Assemble the documentation site's source from the command line arguments."""
    parser = argparse.ArgumentParser(description="Assemble the documentation site's source.")
    parser.add_argument("--out", type=Path, default=Path(".site-src"), help="where to write it")
    parser.add_argument("--root", type=Path, default=Path(), help="the repository (default: here)")
    parser.add_argument("--branch", default="main", help="the branch links to other files point at")
    arguments = parser.parse_args(argv)
    written = build(arguments.root.resolve(), arguments.out, arguments.branch)
    print(f"build_docs_site: {len(written)} pages under {arguments.out}")
    if not theme_stylesheet():
        print(
            "build_docs_site: vibey-engine is not installed, so the site has no Vibey stylesheet",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
