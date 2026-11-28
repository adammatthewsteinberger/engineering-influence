# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Add each built page's search and social metadata: a description, a canonical address, Open Graph and Twitter tags.

Adapted from the same script in the Vibey repository. ProperDocs's plain theme emits none of these, so this reads
the built HTML and inserts them before ``</head>``. It never changes how the site is built, only what is done to the
output afterwards, and it is idempotent: a tag that is already there is left alone, so running it twice gives the same
files. The home page also gets a ``SoftwareApplication`` description for search engines. No image tag is written unless
the site has ``img/social-preview.png``, because a tag that points at nothing is worse than none.

    python scripts/inject_docs_meta.py --site-dir site
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
H1 = re.compile(r"<h1[^>]*>.*?</h1>", re.IGNORECASE | re.DOTALL)
PARAGRAPH = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
TAGS = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")
DESCRIPTION_LIMIT = 155
JSON_LD = 'type="application/ld+json"'
IMAGE = "img/social-preview.png"

# Each tag this script owns, and the attribute text that says it is already in the page.
TAGS_AND_PRESENCE = (
    ('<meta name="description" content="{description}">', 'name="description"', False),
    ('<link rel="canonical" href="{canonical}">', 'rel="canonical"', False),
    ('<meta property="og:title" content="{title}">', 'property="og:title"', False),
    (
        '<meta property="og:description" content="{description}">',
        'property="og:description"',
        False,
    ),
    ('<meta property="og:type" content="website">', 'property="og:type"', False),
    ('<meta property="og:url" content="{canonical}">', 'property="og:url"', False),
    ('<meta property="og:site_name" content="{site_name}">', 'property="og:site_name"', False),
    ('<meta property="og:image" content="{image_url}">', 'property="og:image"', True),
    ('<meta name="twitter:card" content="{card}">', 'name="twitter:card"', False),
    ('<meta name="twitter:title" content="{title}">', 'name="twitter:title"', False),
    (
        '<meta name="twitter:description" content="{description}">',
        'name="twitter:description"',
        False,
    ),
    ('<meta name="twitter:image" content="{image_url}">', 'name="twitter:image"', True),
)


@dataclass(frozen=True)
class SiteConfig:
    """The three site-level values this script reads from the ProperDocs config."""

    site_name: str
    site_description: str
    site_url: str
    repo_url: str


def load_site_config(properdocs_yml: Path) -> SiteConfig:
    """Read the site's name, description, address and repository from the ProperDocs config."""
    data = yaml.safe_load(properdocs_yml.read_text(encoding="utf-8")) or {}
    return SiteConfig(
        site_name=str(data.get("site_name", "")),
        site_description=" ".join(str(data.get("site_description", "")).split()),
        site_url=str(data.get("site_url", "")),
        repo_url=str(data.get("repo_url", "")),
    )


def page_description(html: str, fallback: str) -> str:
    """The first paragraph after the page's first heading, cut at a word to 155 characters, or ``fallback``."""
    heading = H1.search(html)
    paragraph = PARAGRAPH.search(html, heading.end()) if heading else None
    if paragraph is None:
        return fallback
    text = WHITESPACE.sub(" ", TAGS.sub("", paragraph.group(1))).strip()
    if not text:
        return fallback
    if len(text) <= DESCRIPTION_LIMIT:
        return text
    cut = text[:DESCRIPTION_LIMIT]
    boundary = cut.rfind(" ")
    return f"{cut[:boundary] if boundary > 0 else cut}…"


def canonical_url(site_url: str, relative: str) -> str:
    """The address of a page: the site's address, then its path, with ``index.html`` meaning its folder."""
    base = site_url.rstrip("/") + "/"
    if relative in ("", "index.html"):
        return base
    if relative.endswith("/index.html"):
        return f"{base}{relative.removesuffix('index.html')}"
    return f"{base}{relative}"


def escape(value: str) -> str:
    """A value safe inside a double-quoted attribute."""
    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def inject(html: str, values: dict[str, str], json_ld: str | None, with_image: bool) -> str:
    """Insert the tags that are not already in the page before ``</head>``."""
    end = html.lower().rfind("</head>")
    if end == -1:
        return html
    safe = {name: escape(value) for name, value in values.items()}
    block = [
        tag.format(**safe)
        for tag, presence, needs_image in TAGS_AND_PRESENCE
        if presence not in html and (with_image or not needs_image)
    ]
    if json_ld is not None and JSON_LD not in html:
        block.append(f'<script type="application/ld+json">{json_ld.replace("</", "<\\/")}</script>')
    if not block:
        return html
    return f"{html[:end]}{''.join(f'    {line}' + chr(10) for line in block)}{html[end:]}"


def homepage_json_ld(config: SiteConfig, description: str) -> str:
    """A ``SoftwareApplication`` description of the project for search engines, with no version that could go stale."""
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": config.site_name,
            "description": description,
            "url": config.site_url,
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Linux, macOS",
            "license": f"{config.repo_url}/blob/main/LICENSE",
            "codeRepository": config.repo_url,
            "programmingLanguage": "Python",
            "author": {
                "@type": "Person",
                "name": "Adam Matthew Steinberger",
                "url": "https://github.com/adammatthewsteinberger",
            },
        },
        ensure_ascii=False,
    )


def main(argv: list[str] | None = None) -> int:
    """Add search and social metadata to a built documentation site, from the command line."""
    parser = argparse.ArgumentParser(
        description="Add search and social metadata to a built documentation site."
    )
    parser.add_argument("--site-dir", default="site", help="the built site (default: site)")
    parser.add_argument(
        "--properdocs-yml",
        default="properdocs.yml",
        help="the site's config (default: properdocs.yml)",
    )
    arguments = parser.parse_args(argv)
    site = Path(arguments.site_dir)
    config = load_site_config(Path(arguments.properdocs_yml))
    with_image = (site / IMAGE).is_file()
    image_url = f"{config.site_url.rstrip('/')}/{IMAGE}"
    changed = 0
    for page in sorted(site.rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        relative = page.relative_to(site).as_posix()
        found = TITLE.search(html)
        values = {
            "title": found.group(1).strip() if found else config.site_name,
            "description": page_description(html, config.site_description),
            "canonical": canonical_url(config.site_url, relative),
            "site_name": config.site_name,
            "image_url": image_url,
            "card": "summary_large_image" if with_image else "summary",
        }
        json_ld = (
            homepage_json_ld(config, values["description"]) if relative == "index.html" else None
        )
        updated = inject(html, values, json_ld, with_image)
        if updated != html:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"inject_docs_meta: updated {changed} page(s) under {site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
