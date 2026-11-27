# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Scripted answers for a screenplay run's stages, shaped so each one passes its mechanical check.

`answer` returns the scripted text for a screenplay prompt, or None for any other prompt, so the shared rehearsal
server (``smoke_rehearsal``) can ask it first. Nothing here talks to a live model, and the sources are made up.
"""

from typing import Final

SOURCES: Final[dict[str, bytes]] = {
    "source/001.md": b"# Day one\n\nAdam hides the air problem from the crew.\n",
    "source/002.md": b"# Day two\n\nThe stack cracks and the reserve is lost.\n",
}

DIGEST: Final = "Day one: the air problem is hidden. Day two: the stack cracks."
BRIEF: Final = "A short film about a crew that hides a failing air supply until it cannot."

ANCHORS: Final = """## Dramatic spine

Adam hides the colony's failing air from the crew until the stack cracks.

## Opening image

A flat amber line falls across a pressure gauge in an empty bunk room.

## Closing image

The crew stands in the airlock and the light comes on.

## All Is Lost

The stack cracks, the beds die, and the reserve is lost, because Adam kept the number secret.

## Cannot lose

The stack. The page 61 photocopy.

## Can lose

The Iowa letters.

## Structural mode

Kubrick, for progressive revelation of the air supply.
"""

AUDIT: Final = (
    "## Source verdicts\n| Source | Verdict |\n|---|---|\n"
    "| 001 | carries the spine |\n| 002 | a side road |\n\n"
    "## Internalization\n| Character | Wants | Fears |\n|---|---|---|\n| Adam | the crew safe | the dome |\n\n"
    "## Source to beat\n- Set-Up: 001\n\n"
    "## Compression\n- cuts the second drive; keeps the stack\n\n"
    "## Inventions\n- a night watchman, FILM\n"
)

BEAT_RANGES: Final = (
    ("Opening Image", "1 to 1"),
    ("Theme Stated", "5 to 5"),
    ("Set-Up", "6 to 10"),
    ("Catalyst", "12 to 12"),
    ("Debate", "12 to 25"),
    ("Break into Two", "25 to 25"),
    ("B Story", "30 to 30"),
    ("Fun and Games", "30 to 55"),
    ("Midpoint", "55 to 55"),
    ("Bad Guys Close In", "55 to 75"),
    ("All Is Lost", "135 to 145"),
    ("Dark Night of the Soul", "146 to 155"),
    ("Break into Three", "156 to 165"),
    ("Finale", "166 to 175"),
    ("Closing Image", "180 to 180"),
)
BEATS: Final = (
    "| Beat | Pages | Scenes | Scene | Central character | Function |\n|---|---|---|---|---|---|\n"
    + "".join(
        f"| {name} | {pages} | S1 | a scene | Adam | "
        f"{'rupture' if name == 'All Is Lost' else 'none'} |\n"
        for name, pages in BEAT_RANGES
    )
)

CARD_BEATS: Final = (
    "Opening Image",
    "Theme Stated",
    "Set-Up",
    "Catalyst",
    "Debate",
    "Break into Two",
    "All Is Lost",
    "Dark Night of the Soul",
    "Break into Three",
    "Finale",
)
SCENE_CARDS: Final = "".join(
    f"## S{number:02d} · a scene\n"
    f"**What changes:** the crew learns something.\n"
    f"**Therefore:** the next scene follows.\n"
    f"**Beat:** {beat}\n"
    f"**Storyline:** A\n"
    f"**Sources:** 001\n\n"
    for number, beat in enumerate(CARD_BEATS, 1)
)

VISUAL_GRAMMAR: Final = (
    "## Primary sets\n| Set | Light | Colour | Texture |\n|---|---|---|---|\n"
    "| hive | low, amber | brown | wax |\n\n"
    "## Character signatures\n- Adam: a torn green scarf\n"
)


def answer(user: str) -> str | None:
    """The scripted answer to a screenplay prompt, or None when the prompt is not a screenplay stage's."""
    if user.startswith("Condense this source"):
        return DIGEST
    if user.startswith("Write the screenplay brief"):
        return BRIEF
    if user.startswith("Write the anchors"):
        return ANCHORS
    if user.startswith("Audit this novel"):
        return AUDIT
    if user.startswith("Write the beat sheet"):
        return BEATS
    if user.startswith("Write the scene cards"):
        return SCENE_CARDS
    if user.startswith("Write the visual grammar"):
        return VISUAL_GRAMMAR
    return None
