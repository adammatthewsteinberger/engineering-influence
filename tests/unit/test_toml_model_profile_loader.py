# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The profile file is the deployment's, and a mistake in it is reported with the entry it is in."""

import re
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.models.toml_model_profile_loader import (
    TomlModelProfileLoader,
)
from engineering_influence.interfaces.model_profile_loader_interface import (
    ModelProfileLoaderInterface,
)
from engineering_influence.models.model_profile import ModelProfile

DOCS = Path(__file__).parent.parent.parent / "docs" / "MODEL_PROFILES.md"

LOCAL = """
[[profile]]
name = "local"
adapter = "openai_compatible"
provider = "local"
model = "m"
base_url = "http://127.0.0.1:11434"
"""


def load(tmp_path: Path, text: str) -> tuple[ModelProfile, ...]:
    path = tmp_path / "profiles.toml"
    path.write_text(text, encoding="utf-8")
    return TomlModelProfileLoader().load(path)


def refused(tmp_path: Path, text: str) -> str:
    with pytest.raises(ApplicationError) as caught:
        load(tmp_path, text)
    assert caught.value.code == "MODEL_PROFILE_INVALID"
    return caught.value.message


def test_the_loader_is_a_port() -> None:
    assert isinstance(TomlModelProfileLoader(), ModelProfileLoaderInterface)


def test_a_profile_is_read_with_its_defaults(tmp_path: Path) -> None:
    (local,) = load(tmp_path, LOCAL)
    assert (local.name, local.adapter, local.api_key_env, local.output_cap_field) == (
        "local",
        "openai_compatible",
        "",
        "max_tokens",
    )


def test_an_anthropic_profile_may_leave_out_the_base_url(tmp_path: Path) -> None:
    text = (
        '[[profile]]\nname = "h"\nadapter = "anthropic"\nprovider = "a"\nmodel = "m"\n'
        'api_key_env = "ANTHROPIC_API_KEY"\n'
    )
    (hosted,) = load(tmp_path, text)
    assert hosted.base_url == "https://api.anthropic.com"
    assert hosted.requires_key()


def test_an_anthropic_profile_keeps_a_base_url_it_names(tmp_path: Path) -> None:
    text = (
        '[[profile]]\nname = "h"\nadapter = "anthropic"\nprovider = "a"\nmodel = "m"\n'
        'api_key_env = "K"\nbase_url = "https://proxy.example.test"\n'
    )
    (hosted,) = load(tmp_path, text)
    assert hosted.base_url == "https://proxy.example.test"


def test_a_local_server_must_say_where_it_is(tmp_path: Path) -> None:
    message = refused(tmp_path, LOCAL.replace('base_url = "http://127.0.0.1:11434"\n', ""))
    assert "profile #1 (local)" in message
    assert "missing 'base_url'" in message


@pytest.mark.parametrize("key", ["name", "adapter", "provider", "model"])
def test_a_missing_required_key_is_named(tmp_path: Path, key: str) -> None:
    text = re.sub(rf"^{key} = .*\n", "", LOCAL, flags=re.MULTILINE)
    assert f"missing {key!r}" in refused(tmp_path, text)


def test_an_unknown_key_is_refused_so_a_typo_cannot_blank_the_key(tmp_path: Path) -> None:
    message = refused(tmp_path, LOCAL + 'api_key_envv = "X"\n')
    assert "unknown key 'api_key_envv'" in message
    assert "profile #1 (local)" in message


def test_an_unknown_top_level_key_is_refused(tmp_path: Path) -> None:
    assert "unknown top-level key 'profiles'" in refused(tmp_path, LOCAL + "\n[profiles]\n")


def test_a_pasted_key_is_refused_and_not_repeated(tmp_path: Path) -> None:
    secret = "sk-ant-api03-SECRETSECRETSECRET"
    message = refused(tmp_path, LOCAL + f'api_key_env = "{secret}"\n')
    assert secret not in message
    assert "profile #1 (local)" in message


def test_a_value_of_the_wrong_type_is_reported_with_its_entry(tmp_path: Path) -> None:
    assert "profile #1" in refused(tmp_path, LOCAL.replace('"local"\nadapter', "7\nadapter"))


def test_two_profiles_may_not_share_a_name(tmp_path: Path) -> None:
    assert "share a name" in refused(tmp_path, LOCAL + LOCAL)


def test_a_file_with_no_profile_is_refused(tmp_path: Path) -> None:
    assert "no [[profile]] entry" in refused(tmp_path, "")


def test_invalid_toml_is_reported(tmp_path: Path) -> None:
    assert "is not valid TOML" in refused(tmp_path, "[[profile")


def test_a_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as caught:
        TomlModelProfileLoader().load(tmp_path / "absent.toml")
    assert "cannot read" in caught.value.message


def test_the_documented_example_loads(tmp_path: Path) -> None:
    blocks = re.findall(r"```toml\n(.*?)```", DOCS.read_text(encoding="utf-8"), re.DOTALL)
    assert [p.name for p in load(tmp_path, blocks[0])] == ["hosted", "local"]
