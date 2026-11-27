# Screenplays: the author's folders

A screenplay run is written from two folders the author keeps. Neither is committed to this repository.

## The source folder (ADR 0017)

The manuscript the film is made from: each `.md` or `.txt` file in the folder, read in name order, one source per file.
A hidden file is skipped. A file over 2,000,000 bytes is refused rather than cut short, and a file with control characters
is refused, since the text is untrusted. An empty folder is refused (`SOURCE_EMPTY`).

## The bible folder (ADR 0018)

The characters, places and things the film must keep consistent from scene to scene, kept as cards:

```
bible/
  bible.toml              optional: the keys each kind must set
  character/
    ada.md
  place/
    harbour.md
```

- **Kind** is the subfolder name: a lowercase identifier (`character`, `place_name`). **Id** is the file name without `.md`:
  a lowercase identifier that may contain `-` (`ada-lovelace`). An id is unique within its kind.
- A card opens with TOML front matter between two `+++` lines, then Markdown:

  ```
  +++
  name = "Ada Lovelace"
  role = "navigator"
  real = true
  clearance = "Public record: published letters"
  +++

  Ada keeps the log. She sails to [[place: harbour]] at dawn.
  ```

- `bible.toml` names the keys each kind must set:

  ```toml
  [required]
  character = ["name", "role"]
  place = ["name"]
  ```

- A body link `[[kind: id]]` must name a card that exists.
- A card with `real = true` is a real person. It must name its `clearance` (who agreed, or where the fact is public
  record), and it must not carry a `likeness` or `voice` key: the pipeline never prompts a real person's likeness or voice.

A run takes the bible with `--bible DIR`, beside `--source`: `ei book create --kind screenplay --source DIR --bible DIR`.
The cards are checked before the run starts and kept in it. Each scene is handed the cards it names, by their `name` or id
(the `Ada Lovelace` card is named by `Ada Lovelace` or `ada-lovelace`; matching ignores case and needs whole words).

A bible that breaks any of these rules is refused as a whole before a run uses it. The error names the card and the rule.
The error codes are listed in [Troubleshooting](TROUBLESHOOTING.md).

## Scene tone ratio

A scene card may carry `**Tone:**` with `warm`, `conflict` or `neutral`. When any card carries a tone, the scene-card stage
refuses the cards unless the warm scenes are at least five times the conflict scenes, and it names any tone that is not one
of the three. Cards with no tone are not counted, so a screenplay whose cards carry no tone is not checked.

## Drafting checks

Each drafted scene is checked before it is kept. A scene must be exactly one scene and follow the format rules. Its dialogue
must not repeat its sources: a speech that holds twelve words of a source in a row, ignoring case and punctuation, fails the
check, so research is spoken as dialogue rather than read out of a file. Action is not checked, since a description may name
what the sources say. A scene that fails is drafted once more; if the second draft fails too, the stage stops with
`STAGE_OUTPUT_INVALID` and names the first problems.

## Beat positions

After the scenes are revised, the assembled script must place each beat where the beat sheet puts it. Each beat's first
scene card must begin within 5% of the film, by the script's estimated Courier length, of the place the beat sheet gives
for it, and every one of the fifteen beats must have a scene card. The length is measured, not the card count, so a long
opening scene moves the beats after it. A script that fails is refused at assembly with `STAGE_OUTPUT_INVALID`, and the
message names each beat that is missing or out of place.

## The title page

A film's title page prints its title, then the credit and source book the author gives in an optional `title.toml`, kept
beside the source files in the `--source` folder:

```toml
credit = "Based on the novel by A. Writer"
source = "The Example Novel"
```

Each key is optional and is one line of text, at most 200 characters. Any other key, or a value that is not text, refuses
the run with `SCREENPLAY_TITLE_INVALID` and names the problem. The source intake reads only `.md` and `.txt` files, so
`title.toml` is never read as a source.
