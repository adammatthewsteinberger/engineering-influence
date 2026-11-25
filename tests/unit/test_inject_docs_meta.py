"""The script that adds search and social metadata to each built page of the documentation site."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "inject_docs_meta.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("inject_docs_meta", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["inject_docs_meta"] = module
    spec.loader.exec_module(module)
    return module


META = load()
SITE_URL = "https://example.github.io/project/"
CONFIG = (
    "site_name: project\nsite_description: >-\n  A project that does\n  one thing well.\n"
    f"site_url: {SITE_URL}\nrepo_url: https://github.com/example/project\n"
)
PAGE = "<html><head><title>Guide - project</title></head><body><h1>Guide</h1><p>How to <b>start</b>.</p></body></html>"


def site(tmp_path: Path, pages: dict[str, str], image: bool = False) -> Path:
    out = tmp_path / "site"
    for name, html in pages.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(html, encoding="utf-8")
    if image:
        (out / "img").mkdir()
        (out / "img" / "social-preview.png").write_bytes(b"png")
    (tmp_path / "properdocs.yml").write_text(CONFIG)
    return out


def run(tmp_path: Path, out: Path) -> int:
    return int(
        META.main(["--site-dir", str(out), "--properdocs-yml", str(tmp_path / "properdocs.yml")])
    )


# ------------------------------------------------------------------------------ the pieces
def test_the_config_gives_the_name_the_one_line_description_the_address_and_the_repository(
    tmp_path: Path,
) -> None:
    (tmp_path / "properdocs.yml").write_text(CONFIG)

    config = META.load_site_config(tmp_path / "properdocs.yml")

    assert (config.site_name, config.site_description) == (
        "project",
        "A project that does one thing well.",
    )
    assert (config.site_url, config.repo_url) == (SITE_URL, "https://github.com/example/project")


def test_a_config_with_nothing_in_it_gives_empty_values(tmp_path: Path) -> None:
    (tmp_path / "empty.yml").write_text("")

    assert META.load_site_config(tmp_path / "empty.yml").site_name == ""


def test_the_description_is_the_first_paragraph_after_the_first_heading_without_its_tags() -> None:
    assert META.page_description(PAGE, "fallback") == "How to start."


@pytest.mark.parametrize(
    "html", ["<p>no heading</p>", "<h1>x</h1>", "<h1>x</h1><p>   </p>", "<h1>x</h1><p><i></i></p>"]
)
def test_a_page_with_no_usable_paragraph_gets_the_fallback(html: str) -> None:
    assert META.page_description(html, "fallback") == "fallback"


def test_a_long_description_is_cut_at_a_word_and_marked() -> None:
    long = "<h1>x</h1><p>" + " ".join(["word"] * 60) + "</p>"

    text = META.page_description(long, "f")

    assert text.endswith("…") and len(text) <= META.DESCRIPTION_LIMIT + 1 and " " not in text[-2:]


def test_one_unbroken_word_is_cut_where_the_limit_falls() -> None:
    text = META.page_description("<h1>x</h1><p>" + "a" * 400 + "</p>", "f")

    assert text == "a" * META.DESCRIPTION_LIMIT + "…"


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("", SITE_URL),
        ("index.html", SITE_URL),
        ("guide/index.html", SITE_URL + "guide/"),
        ("llms.html", SITE_URL + "llms.html"),
    ],
)
def test_a_pages_address_follows_its_folder(relative: str, expected: str) -> None:
    assert META.canonical_url("https://example.github.io/project", relative) == expected


def test_a_value_is_made_safe_for_a_quoted_attribute() -> None:
    assert META.escape('a "b" <c> & d') == "a &quot;b&quot; &lt;c&gt; &amp; d"


# ------------------------------------------------------------------------------ inserting tags
VALUES = {
    "title": 'A "title"',
    "description": "d",
    "canonical": SITE_URL,
    "site_name": "project",
    "image_url": SITE_URL + "img/social-preview.png",
    "card": "summary",
}


def test_the_tags_go_before_the_end_of_the_head_with_their_values_escaped() -> None:
    out = META.inject(PAGE, VALUES, None, False)

    assert out.index('<meta property="og:title" content="A &quot;title&quot;">') < out.index(
        "</head>"
    )
    assert '<link rel="canonical" href="https://example.github.io/project/">' in out
    assert '<meta name="twitter:card" content="summary">' in out


def test_no_image_tag_is_written_without_an_image() -> None:
    assert "og:image" not in META.inject(PAGE, VALUES, None, False)
    assert "twitter:image" not in META.inject(PAGE, VALUES, None, False)


def test_the_image_tags_are_written_when_there_is_an_image() -> None:
    out = META.inject(PAGE, VALUES, None, True)

    assert f'<meta property="og:image" content="{VALUES["image_url"]}">' in out
    assert f'<meta name="twitter:image" content="{VALUES["image_url"]}">' in out


def test_a_tag_the_page_already_has_is_left_alone_so_a_second_run_changes_nothing() -> None:
    once = META.inject(PAGE, VALUES, "{}", False)

    assert META.inject(once, VALUES, "{}", False) == once
    assert once.count('rel="canonical"') == 1 and once.count("application/ld+json") == 1


def test_a_page_that_already_has_a_description_keeps_its_own() -> None:
    own = PAGE.replace("</head>", '<meta name="description" content="mine"></head>')

    out = META.inject(own, VALUES, None, False)

    assert out.count('name="description"') == 1 and 'content="mine"' in out


def test_a_page_with_every_tag_is_returned_untouched() -> None:
    full = META.inject(PAGE, VALUES, "{}", True)

    assert META.inject(full, VALUES, "{}", True) is full


def test_a_page_with_no_head_is_returned_untouched() -> None:
    assert META.inject("<p>fragment</p>", VALUES, "{}", True) == "<p>fragment</p>"


def test_structured_data_cannot_close_its_own_script_tag() -> None:
    out = META.inject(PAGE, VALUES, '{"x": "</script><script>alert(1)"}', False)

    assert "</script><script>alert" not in out and "<\\/script>" in out


def test_the_description_of_the_project_for_search_engines_names_no_version() -> None:
    config = META.SiteConfig(
        "project", "does one thing", SITE_URL, "https://github.com/example/project"
    )

    data = json.loads(META.homepage_json_ld(config, "does one thing"))

    assert data["@type"] == "SoftwareApplication" and data["codeRepository"] == config.repo_url
    assert data["license"] == "https://github.com/example/project/blob/main/LICENSE"
    assert "softwareVersion" not in data and "downloadUrl" not in data


# ------------------------------------------------------------------------------ the command
def test_every_page_is_updated_and_the_home_page_alone_carries_structured_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = site(tmp_path, {"index.html": PAGE, "guide/index.html": PAGE})

    assert run(tmp_path, out) == 0

    assert "updated 2 page(s)" in capsys.readouterr().out
    assert "application/ld+json" in (out / "index.html").read_text()
    guide = (out / "guide" / "index.html").read_text()
    assert "application/ld+json" not in guide
    assert f'<link rel="canonical" href="{SITE_URL}guide/">' in guide
    assert 'content="Guide - project"' in guide


def test_running_it_twice_changes_nothing_the_second_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = site(tmp_path, {"index.html": PAGE})
    run(tmp_path, out)
    first = (out / "index.html").read_text()
    capsys.readouterr()

    run(tmp_path, out)

    assert (
        "updated 0 page(s)" in capsys.readouterr().out and (out / "index.html").read_text() == first
    )


def test_a_page_with_no_title_is_named_after_the_site(tmp_path: Path) -> None:
    out = site(tmp_path, {"a.html": "<html><head></head><body></body></html>"})

    run(tmp_path, out)

    assert 'property="og:title" content="project"' in (out / "a.html").read_text()


def test_with_an_image_in_the_site_the_card_is_large_and_the_image_is_named(tmp_path: Path) -> None:
    out = site(tmp_path, {"index.html": PAGE}, image=True)

    run(tmp_path, out)

    page = (out / "index.html").read_text()
    assert 'content="summary_large_image"' in page and f"{SITE_URL}img/social-preview.png" in page


def test_the_page_description_falls_back_to_the_sites(tmp_path: Path) -> None:
    out = site(tmp_path, {"a.html": "<html><head></head><body><p>x</p></body></html>"})

    run(tmp_path, out)

    assert (
        'name="description" content="A project that does one thing well."'
        in (out / "a.html").read_text()
    )


def test_the_tags_this_script_writes_are_the_ones_it_checks_for() -> None:
    for tag, presence, _ in META.TAGS_AND_PRESENCE:
        assert presence in tag, tag
    assert len({presence for _, presence, _ in META.TAGS_AND_PRESENCE}) == len(
        META.TAGS_AND_PRESENCE
    )


def test_a_description_that_fits_is_used_whole_even_close_to_the_limit() -> None:
    fits = "w" * (META.DESCRIPTION_LIMIT - 5)

    assert META.page_description(f"<h1>x</h1><p>{fits}</p>", "f") == fits


def test_with_no_image_in_the_site_no_image_tag_is_written_at_all(tmp_path: Path) -> None:
    out = site(tmp_path, {"index.html": PAGE})

    run(tmp_path, out)

    page = (out / "index.html").read_text()
    assert "og:image" not in page and "twitter:image" not in page
    assert 'name="twitter:card" content="summary"' in page
