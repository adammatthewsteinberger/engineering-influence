# ADR 0016: Audible audio is voiced inside ACX; other stores get a locally narrated audiobook

Status: accepted. The routing is in force; the local engine is ADR 0014's (Kokoro is built, its Kyutai fallback is not).

## Context

ACX, the route into Audible, prohibits unauthorized text-to-speech. Amazon's sanctioned AI narration is Virtual Voice
and Voice Replica, both run inside ACX by the rights holder. ADR 0014 chose Kokoro through mlx-audio for narration,
for stores that accept disclosed AI narration.

## Decision

The audiobook phase has two outputs, both optional and off by default:

- **ACX (Audible): text for Virtual Voice.** The `audiobook` stage writes `acx/chapter_NN.txt` (plain, speakable text
  per chapter) and `acx-export.json`, which names Virtual Voice, set up inside ACX, as the narrator. The pipeline
  generates no Audible audio.
- **Non-Audible stores (Google Play Books, Kobo, Spotify): locally narrated audio.** The `narration` stage reads each
  chapter with a narrator named by `EI_NARRATOR`, gates the audio (see ADR 0014), levels it, and writes
  `narration/chapter_NN.wav` and `narration.json`. The manifest carries an AI-narration disclosure. With no narrator
  configured the stage records `not_narrated` and makes nothing. A named narrator is refused until its engine is built.

## Consequences

- Audible and the non-Audible stores never share an audio file. The ACX text is never narrated by this pipeline.
- The listing disclosure for AI narration is required on the non-Audible store listings. The manifest carries it; the
  listing text is not yet changed by this release.
- The Virtual Voice route depends on ACX's current Virtual Voice terms and upload format, which are not checked here.
  Confirm them on ACX's page before uploading the export.
