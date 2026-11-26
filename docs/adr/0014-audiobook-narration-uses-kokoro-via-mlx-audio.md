# ADR 0014: Audiobook narration uses Kokoro-82M through mlx-audio

Status: proposed

## Context

The pipeline ends in a KDP package (interiors, EPUB, covers, metadata). The natural next
output is an audiobook rendered locally on the maintainer's Apple Silicon Mac, with no paid
API. The research behind this decision is in
[`docs/research/open-source-tts-on-macos.md`](../research/open-source-tts-on-macos.md).

Constraints that decided it:

- The audio will be sold, so the model's weights and voices must allow commercial use.
- This repository is MIT. A copyleft engine (Piper is now GPL-3.0) can only run as an outside
  process, never as an imported dependency.
- The Mac has Apple Silicon. Engines without a Metal or Neural Engine path run on the CPU only.
- ACX, the route into Audible, prohibits unauthorized text-to-speech. Audiobooks from this
  pipeline go to stores that accept disclosed AI narration (Google Play Books, Kobo, Spotify).

## Decision

- Default narrator: **Kokoro-82M** (Apache-2.0 weights and voices) run through **mlx-audio**
  (MIT), model `mlx-community/Kokoro-82M-bf16`, with the mlx-audio version pinned.
- Fallback narrator for hosts without MLX (Linux CI, Intel Macs): **Kyutai Pocket TTS** (MIT
  code) on the CPU, limited to voices whose licences have been checked.
- Cloned or designed voices are out of scope for now; when they are needed, **Qwen3-TTS**
  (Apache-2.0) through mlx-audio is the planned engine.
- Rejected: XTTS v2 (non-commercial licence), Bark (unmaintained), Piper as a dependency
  (GPL-3.0), Chatterbox as the default (slower than real time on an M4).

Narration sits behind a `NarratorPort` in `interfaces/` with one adapter per engine in
`infrastructure/`, so the domain never imports an audio library.

## Consequences

- An audiobook stage needs an audio gate: reject a chapter with NaN samples, long silences, or
  a duration outside the expected words-per-minute band, and normalise loudness to the store's
  specification. This guards against a reported mlx-audio defect that produced silent Kokoro
  output.
- `listing.md` gains an AI-narration disclosure, and `docs/BOOKS_AND_KDP.md` must say that the
  audiobook is not for ACX.
- mlx-audio becomes an optional extra (for example `audio`), installable only on macOS arm64,
  so the core package and Linux CI are unaffected.
- Before this ADR is accepted: an A/B listening test of Kokoro against Pocket TTS on ten
  chapters of a real manuscript, with render times on the maintainer's Mac.
