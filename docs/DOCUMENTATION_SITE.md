# The documentation site

**BLUF:** These documents are also published as a website, from the same Markdown, so there is one copy to keep
true. `scripts/build_docs_site.py` assembles the pages, ProperDocs builds them, and the build fails on any link that
goes nowhere. It publishes only when you turn it on: set the repository variable `PUBLISH_DOCS` to `true` and switch
GitHub Pages to "GitHub Actions". The site has no analytics and no tracking, and it has never been published yet.

## One source, two readers

> **Daniel:** A website means a second copy of every page, and a second copy means two things that disagree. I have
> been burned by that before.
>
> **Professor Feynman:** What if there were no second copy? Think of a translator at a border. The speaker says one
> thing, and each listener hears it in their own language.
>
> **Daniel:** So the Markdown is the speaker.
>
> **Professor Feynman:** Yes. On GitHub a link says `../examples`, because it is read from inside the repository. On
> a website that means nothing. So before the build, a script walks every page and translates each link: a link to
> another page becomes a link between the site's pages, and a link to anything else, an example or a source file,
> becomes a link to that file on GitHub.
>
> **Daniel:** And if a link points at something that is not there?
>
> **Professor Feynman:** The build stops. Warnings are errors here, so a link that goes nowhere cannot be published.
> The limit of the picture: the translator can tell that a heading exists, not that the sentence around the link still
> makes sense.
>
> **Daniel:** One source, a translator, and a build that refuses a broken link. I will edit the Markdown and nothing
> else.

## How it fits together

| Piece | What it does |
|---|---|
| `scripts/build_docs_site.py` | Copies each page into `.site-src/` under a clean address (`GETTING_STARTED.md` becomes `getting-started/`), rewrites its links, and builds the page that lists the decision records |
| `properdocs.yml` | The site's name, description, address and navigation. A page that is not in the navigation is an error |
| `docs-site/site.css` | The few rules this site adds to the Vibey stylesheet: the scenes, and a readable width |
| The Vibey stylesheet | Taken from the locked `vibey-engine` package at build time, so no copy of it is committed |
| `scripts/inject_docs_meta.py` | Adds each page's description, canonical address and Open Graph and Twitter tags, and the home page's `SoftwareApplication` description. It adds an image tag only if the site has `img/social-preview.png` |
| `.github/workflows/docs.yml` | On a pull request, builds strictly and publishes nothing. On `develop`, builds and, if `PUBLISH_DOCS` is `true`, publishes |

The site shows the `develop` branch, which documents what is built today. Links to files that are not pages point at
`develop` too, so they match the pages beside them.

## Build it yourself

```bash
uv sync --extra runtime
uv run python scripts/build_docs_site.py --out .site-src
uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict
uv run python scripts/inject_docs_meta.py --site-dir site
python3 -m http.server --directory site 8000     # then open http://127.0.0.1:8000
```

`.site-src/` and `site/` are not committed. Without the `runtime` extra the site builds with no Vibey stylesheet and
says so.

## Publishing it

1. In the repository settings, open **Pages** and set the source to **GitHub Actions**.
2. Set the repository variable `PUBLISH_DOCS` to `true`.
3. Merge to `develop`, or run the **Docs** workflow by hand. The site appears at
   `https://adammatthewsteinberger.github.io/engineering-influence/`.

The `github-pages` environment may carry required reviewers, as the upload environments do.

## What is not verified

- The workflow has never run on GitHub, and nothing is published. The build and the metadata step were run locally
  against ProperDocs 1.6.7, and the pages were looked at in a browser; the deploy step has not been exercised.
- There is no social preview image yet, so shared links show a title and description and no picture.
- The site has not been checked with a screen reader, and its colours are the Vibey stylesheet's, not audited here.
- The home page is the README, whose first screen is written for GitHub and PyPI.
