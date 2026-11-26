# Research: an open-source text-to-speech engine for audiobooks on a Mac

Date: 2026-11-25 · Status: research complete, decision proposed in
[ADR 0014](../adr/0014-audiobook-narration-uses-kokoro-via-mlx-audio.md)

## Bottom line

Use **Kokoro-82M through mlx-audio** as the default narration engine. It is the only
widely used open model with a real Apple Silicon GPU path (MLX/Metal), its weights and voices
are Apache-2.0 and its runtime is MIT, so audio can be sold and the code can sit in this
MIT repository. Keep **Kyutai Pocket TTS** as a CPU fallback and **Qwen3-TTS** (also through
mlx-audio) for the day a book needs cloned or designed voices.

The bigger finding is about distribution, not engines: **ACX (the route into Audible) rejects
audiobooks made with unauthorized text-to-speech.** Whatever engine we pick, the audiobook output
is for Google Play Books, Kobo, Spotify/Findaway and similar stores, with AI-narration
disclosure. Audible is reachable only through Amazon's own Virtual Voice.

## 1. Question

Framed with PICO and checked with FINER (see the `research-methodology` skill):

| | |
|---|---|
| Population | Books produced by engineering-influence, rendered on the maintainer's Apple Silicon MacBook Pro (arm64, macOS) |
| Intervention | An open-source TTS engine that turns a finished manuscript into chapter audio |
| Comparison | The other open-weight engines that run locally on macOS |
| Outcome | Narration quality over long text, speed on Apple Silicon, licence fit for *selling* the audio and for an MIT codebase, maintenance health, install friction |

FINER: feasible (runs offline on the existing Mac, no paid API), relevant (the next output after
the KDP package), novel for this repo (nothing in `src/` or `docs/` handles audio today).

### Inclusion criteria

1. Code and weights under an open licence that permits **commercial** use of the output.
2. Runs locally on macOS arm64 without CUDA.
3. Active maintenance in 2026.
4. Narration quality good enough for long-form non-fiction; voice cloning is a bonus, not a requirement.
5. Licence compatible with an MIT repository (copyleft is acceptable only as an external process, never bundled).

## 2. Method

Web search on 2026-11-25, standard engine, followed by fetches of primary pages (model cards,
PyPI pages, project READMEs, the ACX help centre). Every source was screened with CRAAP
(Currency, Relevance, Authority, Accuracy, Purpose) and the SIFT habit of tracing claims to the
original. Vendor blogs and SEO round-ups were used only to find candidates; licence and
platform claims were traced to the model card, repository or platform page before they were
relied on.

### Search log

| # | Query | Useful results | Used for |
|---|---|---|---|
| 1 | `best open source TTS models 2026 Apple Silicon local` | 19 | Candidate list; Mac-specific round-up |
| 2 | `Kokoro TTS mlx-audio Mac` | 18 | MLX runtime, known MLX defect |
| 3 | fetch promptquorum.com best-local-tts-mac | 1 | Per-engine Apple Silicon status and licences |
| 4 | `Piper TTS archived OHF-Voice piper1-gpl GPL license` | 14 | Piper's move and licence change |
| 5 | `Kyutai Pocket TTS CPU Mac license` | 20 | CPU-first alternative, voice licence caveat |
| 6 | `hexgrad Kokoro-82M Apache 2.0 voices model card` | 19 | Primary licence evidence |
| 7 | `Chatterbox Resemble AI MIT Apple Silicon mps` | 15 | Cloning candidate, Apple Silicon speed |
| 8 | `Qwen3-TTS license Apache 2.0 voice cloning mlx` | 19 | Cloning candidate, licence, sizes |
| 9 | `ACX Audible AI narrated audiobooks policy 2026 …` | 19 | Distribution constraint |
| 10 | `mlx-audio release Blaizzy GitHub 2026` | 18 | Maintenance health of the runtime |

### Source quality

| Source | Type | CRAAP verdict |
|---|---|---|
| Hugging Face model cards (hexgrad/Kokoro-82M, kyutai/pocket-tts, ResembleAI/chatterbox, Qwen) | Primary | High: author-published licence and specs |
| Qwen3-TTS technical report, arXiv 2601.15621 | Primary, preprint | High for licence and capabilities; benchmark claims are the authors' own |
| PyPI pages (mlx-audio, kokoro-mlx, chatterbox-mlx, pocket-tts), Homebrew formula | Primary | High for install method and licence |
| ACX help centre, audio submission requirements | Primary, platform | High; the deciding source for distribution |
| OHF-Voice/piper1-gpl repository and releases | Primary | High |
| PromptQuorum Mac TTS guide (Sept 2026) | Secondary | Medium: current and specific, but a content site; its licence claims match the primary sources |
| Pinggy, LocalAIMaster, FindSkill, SiliconFlow round-ups | Secondary/commercial | Low to medium: used for discovery only |
| Narration Box, InkfluenceAI, TomeVox posts on ACX | Commercial blogs | Low: they conflict with each other; resolved against the ACX page itself |
| Single Hugging Face discussion reporting NaN output | Primary, anecdotal | Medium: one report, but specific and reproducible |

## 3. Findings

### Candidates compared

| Engine | Licence (code / weights) | Apple Silicon path | Cloning | Fit |
|---|---|---|---|---|
| **Kokoro-82M** via mlx-audio | MIT / Apache-2.0 | Yes: MLX on Metal | No (54 preset voices) | **Pick** |
| Kyutai **Pocket TTS** | MIT / CC-BY-4.0 with prohibited uses; voice licences vary | CPU by design, real time on M-series | Yes | Fallback |
| **Qwen3-TTS** 0.6B / 1.7B via mlx-audio | Apache-2.0 / Apache-2.0 | Yes: MLX | Yes, from ~3 s of audio | Later, for voices |
| Chatterbox (Resemble AI) | MIT / MIT | MLX fork, below real time | Yes | Possible, slow |
| Piper | GPL-3.0 (new home) | CPU only | No | Excluded as a bundled dependency |
| XTTS v2 (Coqui) | non-commercial CPML | CPU only on Mac | Yes | Excluded: cannot sell output |
| Bark | MIT | Experimental | Partial | Excluded: unmaintained |

### Evidence per engine

**Kokoro-82M.** The model card declares an Apache-2.0 licence and a StyleTTS 2 base,
and states that its Apache-licensed weights can be deployed anywhere from production to
personal projects. It is small, 82M parameters, and its English voice packs are Apache-2.0 as
well (per a Core AI conversion that redistributes them). A Sept 2026 Mac-specific comparison
found Kokoro to be the only engine with a real Metal GPU path, through the community
mlx-audio project; it also notes that Intel Macs cannot use that path. The runtime,
mlx-audio, is MIT-licensed, maintained by Prince Canuma, has more than 8,000 GitHub stars, and shipped v0.6.1 in
October 2026. Usage is one call: `load_model("mlx-community/Kokoro-82M-bf16")` then
`model.generate(text, voice="af_heart")`. A faster Core ML build runs on the Neural Engine and
claims roughly 2x the speed of MLX on the same hardware.

*Risk:* one user reported that the MLX Kokoro build returned NaN or silent audio for every
voice on an M3 Max with mlx-audio 0.4.4. That argues for pinning the runtime version and gating
every chapter's audio for NaN, silence and duration, not against the engine.

**Pocket TTS (Kyutai).** A 100M-parameter model released in January 2026 that runs in real
time on a CPU, with five more languages added in April. Kyutai published the full training stack and reports
about 6x real time on a MacBook Air M4 CPU. It installs with `brew install pocket-tts`
(formula licence MIT). *Caveat:* the code is MIT, but a Core ML conversion carries the
upstream CC-BY 4.0 licence with attribution and prohibited-use terms, and per-voice licences
differ. Each voice we ship would need its licence checked, which is why it is the fallback
and not the default.

**Qwen3-TTS (Alibaba Qwen).** The technical report releases tokenizers and models under
Apache 2.0 and supports 3-second voice cloning and description-based voice design. Sizes:
the 1.7B base is 4.54 GB and the 0.6B base 2.52 GB, and it runs under mlx-audio. Right for multi-character fiction or a
consistent house voice; heavier than needed for default narration.

**Chatterbox.** MIT-licensed and multilingual. On an M4 the MLX-optimised fork measures a
real-time factor of about 0.65-0.74 (slower than real time) in hybrid MLX mode. Outputs carry Resemble's PerTh
watermark. Usable, but a 100,000-word book would take longer than its own playback.

**Piper.** The original rhasspy/piper was archived in October 2025, and development moved to
OHF-Voice/piper1-gpl under GPL-3.0. It also embeds GPL-licensed espeak-ng. Fine as
an external process, but it may not be imported into this MIT package, and it has no GPU path.

**XTTS v2 and Bark.** XTTS v2's licence is non-commercial (CPML), which rules out sold
audiobooks; Bark has had no commits since April 2024.

### Distribution constraint (decisive for product scope)

ACX's own submission requirements say an audiobook must be human-narrated unless otherwise
authorized, and that unauthorized TTS, AI or automated recordings are prohibited. Some
commercial blogs claim ACX now accepts AI narration; the primary ACX page contradicts them,
so they were discarded. Amazon's sanctioned AI routes are its own Virtual Voice and Voice
Replica. Outside Amazon, Google Play Books officially supports AI-narrated audiobooks and
Kobo Writing Life accepts them. The EU AI Act adds disclosure obligations for AI-generated
audio from August 2026.

So an engineering-influence audiobook is a **non-Audible** deliverable, and its listing
metadata must carry an AI-narration disclosure.

## 4. Recommendation

1. Default engine: Kokoro-82M via mlx-audio, model `mlx-community/Kokoro-82M-bf16`, runtime
   version pinned. Behind a `NarratorPort` in `interfaces/`, with the adapter in
   `infrastructure/`, per the onion rules in `AGENTS.md`.
2. Fallback adapter: Pocket TTS on CPU, used when MLX is unavailable (CI on Linux, Intel Macs),
   with an allow-list of voices whose licences have been checked.
3. Deferred: Qwen3-TTS for cloned or designed voices, behind the same port.
4. Gate every chapter's audio: no NaN samples, no silence over a threshold, duration within a
   band of words-per-minute, loudness normalised to the target store's spec.
5. Add an AI-narration disclosure to the listing metadata, and state in
   `docs/BOOKS_AND_KDP.md` that audiobooks are not for ACX.

## 5. Limitations

- No engine was benchmarked on this Mac for this report. Speeds are the projects' own or a
  single third party's figures. A 10-chapter A/B listening test on a real manuscript should
  precede the ADR moving to "accepted".
- "Best" here is weighted for local Mac use and commercial licensing. Arena-style leaderboards
  rank larger, sometimes non-commercial models above Kokoro on raw quality.
- Audiobook platform policies are moving quickly; re-check the ACX page before any release.

## Sources

- hexgrad. "Kokoro-82M." Hugging Face model card. https://huggingface.co/hexgrad/Kokoro-82M
- Blaizzy (Prince Canuma). "mlx-audio." GitHub and PyPI. https://github.com/Blaizzy/mlx-audio · https://pypi.org/project/mlx-audio/
- Kuepper, Hans. "Best Local TTS Engine for Mac (2026)." PromptQuorum, September 11, 2026. https://www.promptquorum.com/power-local-llm/best-local-tts-mac
- PromptQuorum. "MLX-Audio Review." https://www.promptquorum.com/power-local-llm/mlx-audio-review
- "MLX Kokoro TTS produces NaN / silent audio on Apple Silicon." Hugging Face discussion. https://huggingface.co/mlx-community/Kokoro-82M-bf16/discussions/5
- mattmireles. "Kokoro 82M TTS, Surgically Optimized for Apple Silicon." https://huggingface.co/mattmireles/kokoro-coreml
- Kyutai. "Pocket TTS." https://kyutai.org/tts/ · https://github.com/kyutai-labs/pocket-tts · https://formulae.brew.sh/formula/pocket-tts
- slaughters85j. "Pocket TTS (Core ML)." https://huggingface.co/slaughters85j/pocket-tts-coreml
- AlphaSignal. "Kyutai Opens Pocket TTS Training." https://alphasignal.ai/news/kyutai-opens-pocket-tts-training-so-anyone-can-build-cpu-voice-cloning
- Qwen Team. "Qwen3-TTS Technical Report." arXiv:2601.15621, January 22, 2026. https://arxiv.org/abs/2601.15621
- Willison, Simon. "Qwen3-TTS." January 22, 2026. https://simonwillison.net/2026/Jan/22/qwen3-tts
- Resemble AI. "Chatterbox." https://huggingface.co/ResembleAI/chatterbox · "chatterbox-mlx." https://pypi.org/project/chatterbox-mlx/
- Open Home Foundation. "piper1-gpl." https://github.com/OHF-Voice/piper1-gpl
- ACX. "ACX Audio Submission Requirements." https://help.acx.com/s/article/acx-audio-submission-requirements
- InkfluenceAI. "Can You Publish AI-Narrated Audiobooks on Audible?" https://www.inkfluenceai.com/blog/ai-narration-audible-acx-policy-2026
- The New Publishing Standard. https://thenewpublishingstandard.com/?p=15959
- OKMiku. "EU AI Act, ACX, and the disclosure rules." https://okmiku.com/blog/tts-disclosure-rules-eu-acx-2026
