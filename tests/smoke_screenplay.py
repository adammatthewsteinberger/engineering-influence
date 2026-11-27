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

BEATS_IN_ORDER: Final = (
    "Opening Image",
    "Theme Stated",
    "Set-Up",
    "Catalyst",
    "Debate",
    "Break into Two",
    "B Story",
    "Fun and Games",
    "Midpoint",
    "Bad Guys Close In",
    "All Is Lost",
    "Dark Night of the Soul",
    "Break into Three",
    "Finale",
    "Closing Image",
)
# Every scene below is the same length, so beat k of fifteen sits at k/15 of the script. Each beat is planned on the page
# that place falls on (twelve pages a beat, a film of 180), except All Is Lost, which the beat sheet puts at 127 (70%) so
# that it is three-quarters through in the card count as well (eleven of fifteen cards, 73%).
PAGE_OF: Final = {
    beat: 127 if beat == "All Is Lost" else 12 * index + 1
    for index, beat in enumerate(BEATS_IN_ORDER)
}
BEAT_RANGES: Final = tuple((beat, f"{PAGE_OF[beat]} to {PAGE_OF[beat]}") for beat in BEATS_IN_ORDER)
BEATS: Final = (
    "| Beat | Pages | Scenes | Scene | Central character | Function |\n|---|---|---|---|---|---|\n"
    + "".join(
        f"| {name} | {pages} | S1 | a scene | Adam | "
        f"{'rupture' if name == 'All Is Lost' else 'none'} |\n"
        for name, pages in BEAT_RANGES
    )
)

CARD_BEATS: Final = BEATS_IN_ORDER
SCENE_CARDS: Final = "".join(
    f"## S{number:02d} · a scene\n"
    f"**What changes:** the crew learns something.\n"
    f"**Therefore:** the next scene follows.\n"
    f"**Beat:** {beat}\n"
    f"**Storyline:** A\n"
    f"**Sources:** 001\n\n"
    for number, beat in enumerate(CARD_BEATS, 1)
)
# One scene of the same shape for every card: a heading, one action line, and one speech. No digits in the speech,
# and no run of source words, so the scene passes the format and dialogue checks.
SCENE: Final = (
    "INT. ROOM - DAY\n\nAdam watches the gauge fall.\n\nADAM\nThe crew stays in the room.\n"
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
    if user.startswith("Write the scene for this card"):
        return SCENE
    if user.startswith("Revise this scene so it serves its card"):
        return SCENE
    if user.startswith("Revise this scene's structure."):
        return SCENE
    if user.startswith("Sharpen the dialogue in this scene."):
        return SCENE
    return None
