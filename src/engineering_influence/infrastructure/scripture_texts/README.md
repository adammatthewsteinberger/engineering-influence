# Bundled Scripture texts

Six translations, one gzipped file each (`<translation>.txt.gz`): one line per verse, `BOOK C:V<TAB>text`.

| File | Translation | Notes |
|---|---|---|
| `kjv.txt.gz` | King James Version (2006 edition as published by eBible.org) | Protestant canon |
| `web.txt.gz` | World English Bible | includes the deuterocanon |
| `asv.txt.gz` | American Standard Version | 16 KJV-only passages are absent |
| `ylt.txt.gz` | Young's Literal Translation | verse numbers as in the KJV |
| `dra.txt.gz` | Douay-Rheims 1899 | Douay versification (Psalms differ from the KJV); the psalm titles are inside verse 1 |
| `bsb.txt.gz` | Berean Standard Bible | 16 KJV-only passages are absent |

All six are catalogued as public domain by eBible.org (https://ebible.org). `SOURCES.md` records the SHA-256 of each
USFM archive they were built from. Rebuild with `scripts/scripture/build_bundle.py`. The files are data, never run.
