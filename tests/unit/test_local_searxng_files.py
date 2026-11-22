# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The shipped local SearXNG: JSON on, bound to the loopback interface, and no default secret."""

from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[2] / "examples" / "searxng"
COMPOSE = (DIRECTORY / "docker-compose.yml").read_text(encoding="utf-8")
SETTINGS = (DIRECTORY / "settings.yml").read_text(encoding="utf-8")


def lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if not line.strip().startswith("#")]


def test_the_json_format_is_switched_on_because_the_adapter_needs_it() -> None:
    settings = lines(SETTINGS)
    assert "search:" in settings and "formats:" in settings
    assert "- json" in settings and "- html" in settings
    assert "use_default_settings: true" in settings


def test_the_settings_hold_no_secret_key_and_the_compose_file_demands_one() -> None:
    assert "secret_key" not in SETTINGS
    assert 'SEARXNG_SECRET: "${SEARXNG_SECRET:?' in COMPOSE


def test_it_is_published_on_the_loopback_interface_only() -> None:
    ports = [line for line in lines(COMPOSE) if line.startswith("ports:")]
    assert len(ports) == 1 and '"127.0.0.1:' in ports[0]
    assert "0.0.0.0" not in COMPOSE


def test_the_container_drops_capabilities_and_cannot_gain_privileges() -> None:
    compose = lines(COMPOSE)
    assert "cap_drop: [ALL]" in compose
    assert "cap_add: [CHOWN, SETGID, SETUID]" in compose  # exactly what the image needs
    assert 'security_opt: ["no-new-privileges:true"]' in compose


def test_the_settings_are_mounted_read_only_and_the_limiter_is_off_for_one_local_user() -> None:
    assert "- ./settings.yml:/etc/searxng/settings.yml:ro" in lines(COMPOSE)
    assert "limiter: false" in lines(SETTINGS)
    assert "public_instance: false" in lines(SETTINGS)
