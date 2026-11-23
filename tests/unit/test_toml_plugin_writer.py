# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlPluginWriter writes bundles that the plugin parser reads back exactly, the same bytes every time."""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.plugins.toml_plugin_writer import TomlPluginWriter
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.plugin_writer_interface import PluginWriterInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill

WRITER = TomlPluginWriter()
PARSER = TomlPluginParser(TomlSkillParser())


def round_trip(plugin: Plugin) -> Plugin:
    return PARSER.parse(WRITER.render(plugin), plugin.name)


def test_it_is_a_writer() -> None:
    assert isinstance(WRITER, PluginWriterInterface)


def test_a_bundle_of_both_kinds_of_server_and_a_skill_reads_back_the_same() -> None:
    plugin = Plugin(
        "pack",
        3,
        "Does things",
        servers=(
            PluginServer(
                "local", command=("/usr/bin/x", "--flag", 'a "quoted" arg'), env=("A", "B")
            ),
            PluginServer("plain", command=("/usr/bin/y",)),
            PluginServer("remote", url="https://x.example/mcp", bearer_env="TOKEN"),
            PluginServer("remote-open", url="https://y.example/mcp"),
        ),
        skills=(
            Skill("alpha", 1, (), sections=(("One", "text one"), ('Two "2"', "line\nbreak \\ é"))),
            Skill("beta", 2, parts=(("outline", "outline text"),), description="Beta skill"),
        ),
    )
    assert round_trip(plugin) == plugin


def test_the_same_plugin_is_the_same_bytes() -> None:
    plugin = Plugin("pack", 1, skills=(Skill("a", 1, (), sections=(("T", "x"),)),))
    assert WRITER.render(plugin) == WRITER.render(plugin)
    assert WRITER.render(plugin).endswith(b"\n")


def test_nothing_is_written_for_what_is_absent() -> None:
    text = WRITER.render(
        Plugin("pack", 1, servers=(PluginServer("s", command=("/bin/x",)),))
    ).decode()
    assert "description" not in text and "env" not in text and "[[skill]]" not in text
    assert (
        "bearer_env"
        not in WRITER.render(
            Plugin("pack", 1, servers=(PluginServer("s", url="https://x.example/mcp"),))
        ).decode()
    )


safe = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Cf", "Zl", "Zp", "Co")), min_size=1
)


@settings(deadline=None, max_examples=60)
@given(
    title=safe.filter(
        lambda t: (
            t.isprintable() and t == t.strip() and "<" not in t and ">" not in t and len(t) <= 100
        )
    ),
    text=safe,
)
def test_any_title_and_text_survives_the_round_trip(title: str, text: str) -> None:
    try:
        plugin = Plugin("pack", 1, skills=(Skill("a", 1, (), sections=((title, text),)),))
    except ValueError:
        assume(False)
        return
    assert round_trip(plugin) == plugin


def test_an_address_server_is_written_with_no_command_or_env_line() -> None:
    text = WRITER.render(
        Plugin("pack", 1, servers=(PluginServer("s", url="https://x.example/mcp", bearer_env="T"),))
    ).decode()
    assert "command" not in text and "env =" not in text
