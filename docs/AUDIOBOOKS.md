# Audiobooks

An optional phase after the build makes two outputs. Both are off by default.

## For Audible (ACX): text and audio for each part

The `audiobook` stage writes the four parts ACX asks for, each as text and as audio:

| ACX upload | Text | Audio |
|---|---|---|
| Opening credits | `acx/opening-credits.txt` | `acx/audio/opening-credits.wav` |
| Chapters (one per chapter) | `acx/chapter_NN.txt` | `acx/audio/chapter_NN.wav` |
| Closing credits | `acx/closing-credits.txt` | `acx/audio/closing-credits.wav` |
| Retail sample (first 300 words of chapter 1) | `acx/retail-sample.txt` | `acx/audio/retail-sample.wav` |

The audio is read by the narrator named in `EI_NARRATOR`, gated and levelled the same way as the other-store audiobook
below. `acx-export.json` records each part's outcome.

**Virtual Voice is not assumed.** Amazon's Virtual Voice is available only after you apply for access inside ACX. The
text files are the script for it, to paste into ACX if access is granted. Nothing here assumes you have that access.

**Check ACX's terms first.** ACX prohibits unauthorized text-to-speech. This pipeline does not upload anything, and the
audio it writes is for your review. Read ACX's current terms on synthetic narration, and its upload format, before you
upload any of it. The credit wording and the sample length are drafts: ACX's own credit and sample rules are not checked
here.

The built-in narrator is `kokoro`: Kokoro-82M through mlx-audio, installed with the `audio` extra on an Apple Silicon Mac. A name in `EI_NARRATOR` other than `kokoro` is refused with `NARRATOR_UNAVAILABLE`. The listening test ADR 0014 asked for has not been run; the maintainer chose to ship the engine first. With `EI_NARRATOR` unset,
`acx-export.json` says the audio was not narrated, and the text is still written.

A part whose audio the gate refuses is reported as `ACX_AUDIO_REJECTED`, and one whose narrator fails as
`ACX_AUDIO_FAILED`. Both are reported without stopping the run, and a chapter with no speakable words is reported as
`ACX_EMPTY_CHAPTER`.

## For other stores: a locally narrated audiobook

The `narration` stage reads each chapter with a narrator named in `EI_NARRATOR`. Audio that is not numbers between
-1 and 1, goes silent for more than two seconds, or runs outside 90 to 220 words a minute is not kept. Kept audio is
levelled to about -19 dBFS RMS, with peaks kept under -1 dBFS.

No narrator engine is built into this release. Setting `EI_NARRATOR` is refused until one is added (ADR 0014 follows a
listening test). The manifest, `narration.json`, carries an AI-narration disclosure. Store listings for these
audiobooks must carry the same disclosure, which this release does not yet add to the listing.

Do not upload the narrated audiobook to Audible. Google Play Books, Kobo and Spotify accept disclosed AI narration;
confirm each store's current rule before you upload.

The narration stage also refuses a chapter with no speakable text (`AUDIO_NO_TEXT`) or a narrator that changes its
sample rate mid-chapter (`AUDIO_RATE_CHANGED`); both are reported without stopping the run.
