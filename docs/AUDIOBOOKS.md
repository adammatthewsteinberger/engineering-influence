# Audiobooks

An optional phase after the build makes two outputs. Both are off by default.

## For Audible (ACX): text for Virtual Voice

The `audiobook` stage writes the four things ACX asks for, as text for Virtual Voice:

| ACX upload | File | What the pipeline does |
|---|---|---|
| Opening credits | `acx/opening-credits.txt` | Drafts the title and the author's name. The narrator line is for you to add in ACX. |
| Chapters (one per chapter) | `acx/chapter_NN.txt` | The chapter's speakable text, with its heading first. |
| Closing credits | `acx/closing-credits.txt` | Drafts a closing line from the title and author. |
| Retail sample | `acx/retail-sample.txt` | The opening of chapter 1, up to 300 words. Set the length ACX requires when you choose the sample. |

`acx-export.json` names Amazon's Virtual Voice (set up inside ACX) as the narrator and sets
`review_before_upload` to true. The credit wording and the sample length are drafts: ACX's own credit and sample rules
are not checked by this pipeline, so read them on ACX's page before uploading.

This pipeline does not generate Audible audio. ACX prohibits unauthorized text-to-speech. To use Virtual Voice,
upload the text in ACX and choose the narrator there. Check ACX's current Virtual Voice terms and upload format on
ACX's own page before you upload.

## For other stores: a locally narrated audiobook

The `narration` stage reads each chapter with a narrator named in `EI_NARRATOR`. Audio that is not numbers between
-1 and 1, goes silent for more than two seconds, or runs outside 90 to 220 words a minute is not kept. Kept audio is
levelled to about -19 dBFS RMS, with peaks kept under -1 dBFS.

No narrator engine is built into this release. Setting `EI_NARRATOR` is refused until one is added (ADR 0014 follows a
listening test). The manifest, `narration.json`, carries an AI-narration disclosure. Store listings for these
audiobooks must carry the same disclosure, which this release does not yet add to the listing.

Do not upload these audiobooks to ACX or to Audible.

A name in `EI_NARRATOR` is refused with `NARRATOR_UNAVAILABLE` until an engine is built.

The narration stage also refuses a chapter with no speakable text (`AUDIO_NO_TEXT`) or a narrator that changes its sample rate mid-chapter (`AUDIO_RATE_CHANGED`); both are reported without stopping the run.
