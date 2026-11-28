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

## Revision colours

A revision is marked against the shooting script it was revised from. Give the earlier run's `shooting_script.fountain` and
the revision's number:

```bash
ei book create --kind screenplay --source DIR --previous-script earlier/shooting_script.fountain --revision 2
```

Revision 1 is Blue, 2 is Pink, and so on through the standard order to 9. A scene is matched to its baseline scene by its
number, so a scene keeps its identity when others are added or cut. A new scene, or one whose text changed, gets a
`[[revised: Colour *]]` note above its heading. The marked script is stored as `revision_pages.fountain`; the shooting script
itself is unchanged. The page layout that prints the colours is covered in Printed revision marks below.

## Revision checks

A revised scene is kept only if it passes the same checks as the draft (one scene, the format rules), keeps its length
within 10% of the draft, and does not copy its sources into dialogue: the same twelve-word rule as the draft stage, applied
to the source files the card names. A revision that fails any of these keeps its draft; the revision stage does not stop.
Bible cards are not checked at this stage, so a revision that speaks a card's own text is not refused here.

## Print layout

The rendered screenplay PDF is checked against the KDP print layout before it is kept, with the same rules as a book's
interior: text must sit at least the KDP gutter for the film's page count from the binding edge (0.375 inch up to 150
pages, 0.5 inch up to 300, and so on), at least a quarter inch from the outside, top and bottom edges, and no more than
two blank pages in a row. A PDF that breaks these stops the render stage with `STAGE_OUTPUT_INVALID`, and the message
names each page that breaks a rule. The check runs on the typeset PDF, so it measures what will be printed.

## Printed revision marks

When a run has revision pages (see Revision colours above), the printed PDF is typeset from them rather than from the
shooting script. Each changed scene's heading has a bar and a star in the left margin, in its revision colour (Blue for
revision 1, Pink for 2, and so on through Tan for 9). The colours are approximations of the studio colours, not a
published standard. Every page after the title page of a revision carries a running header with the revision and its date, for example `Revision: Pink (2026-11-27)`. The title page has no header.

The revision pages' title page names the revision and its date, for example `Revision: Pink (2026-11-27)`. The date is
`--revision-date`, or today when a baseline is given without one. It is kept with the run, so a resumed run prints the
same date.

## Video

The video stage runs after the script is locked. It plans a shot list from the locked script (`shooting_script.fountain`
when the lock stage stored one, otherwise `screenplay.fountain`) and always stores `video/manifest.json`. What happens
next depends on `EI_VIDEO_PROVIDER` (see [Configuration](CONFIGURATION.md)):

- **Unset, the default.** The stage spends nothing. The manifest has `"status": "not_generated"` and
  `"ai_generated": false`, gives the reason, and lists the planned shots, so the run finishes with a record that no video
  was made.
- **`openrouter`.** The stage prices the shots not yet stored. If they cost more than the run's remaining budget, the run
  stops and waits for your consent rather than spending past the cap. Otherwise it generates each missing shot as
  `video/shot_NNN.mp4` and stores a manifest with `"status": "generated"` and `"ai_generated": true`, which marks the
  film as AI-generated. A shot already stored is never generated again, so `--resume` after a failure pays only for the
  shots still missing. A shot whose generation fails is not stored; the shots already made are kept.

The stage's failures are `VIDEO_PROVIDER_UNAVAILABLE` (the provider is unknown, or its key is missing),
`VIDEO_GENERATION_FAILED` (the service ended a shot's job as failed, cancelled or expired) and `VIDEO_REJECTED` (the
service refused a request). [Troubleshooting](TROUBLESHOOTING.md) gives the fix for each.

Each shot is a paid job. No paid run against a real video provider has been made yet: that pilot needs the maintainer's
approval and a budget.

## The stages this page does not describe above

These stages run in a screenplay's order, after the scene cards (see the plan in `ScreenplayRecipes`). The stages marked
"no model call" are deterministic.

| Stage | Writes | What it does |
|---|---|---|
| `anchors` | `anchors.md` | Writes the anchors of the screenplay adapted from its source: the spine, the opening and closing images, All Is Lost, what can and cannot be lost, and the structural mode. |
| `visual_grammar` | `visual_grammar.md` | Writes the light, colour and texture of each primary set, and a visual signature for each major character. |
| `digest_sources` | `digest/NNN.md` | Condenses each `source/NNN.md` into a digest. A digest already stored is kept, so a run that stops and resumes condenses only what is missing. No digest is written for a source the model has not finished. |
| `revise_scenes` | `revised/NNN.md` | Revises each drafted scene in one call. A revision is kept only if it passes the same section check as the draft and is within the allowed length range of the draft; otherwise the drafted scene is stored unchanged. |
| `structure_scenes` | the structured scene | The structure pass over each revised scene: the card's event must happen on screen and turn the story toward its next beat. The same events, about the same length. |
| `dialogue_scenes` | the dialogue scene | The dialogue pass over each structured scene: cut lines that explain what the audience can see, keep the lines that carry the plot. The same events, about the same length. |
| `assemble_script` | the assembled script | No model call. Each card's revised scene becomes one scene; a scene with two headings is refused. The whole script must pass the Fountain format rules, and the beats must fall where the beat sheet puts them, measured in the script's length. |
| `lock_script` | `shooting_lock.json` | No model call. Each scene card is one scene of the script, in card order, and the stage stops when the two disagree, naming both counts. Scene numbers are planned from a previous lock when the run was given one as `previous_shooting_lock.json`. |
| `log_revisions` | `revision_log.md`, `source_mapping.md` | No model call. A scene whose stored revision is the draft unchanged is recorded as not used, which is what the revision stage stores when it rejects a revision or runs out of money. The stage stops when the lock and the cards disagree. |
| `render_script` | `screenplay.pdf`, `render.md` | Typesets the script with LaTeX and checks the PDF against the KDP print layout and the length ceiling. A script that does not typeset, or a PDF that breaks the layout, stops the stage. |
| `build_epub` | `screenplay.epub` | Builds the EPUB and checks it with epubcheck. An EPUB that fails the check is not stored, and the stage stops with the first findings. |
| `video` | `video/shot_NNN.mp4`, `video/manifest.json` | Plans the shots from the script and, when a video provider is configured, generates the missing ones. See [Video](#video). |
