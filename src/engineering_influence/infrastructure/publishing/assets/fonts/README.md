# Interior fonts

The print interiors (`fine-book.cls`) load these files by path instead of from the TeX installation.
`BookBuilder` copies this folder to `build/<slug>/fonts/` next to the class before LuaLaTeX runs.

Why they are vendored: TeX distributions package EB Garamond differently. TeX Live 2026 ships
`EBGaramond-Initials.otf` with the rest of the family; Debian and Ubuntu ship the initials in a separate
package, so a CI runner built from `texlive-fonts-extra` stopped at `fine-book.cls` with
"The font EBGaramond-Initials cannot be found" for every book. Different font builds also change line
breaks and page counts, and the cover spine width is computed from the page count, so one set of font
files is part of the build's determinism, the same way `SOURCE_DATE_EPOCH` pins the PDF dates.

| File | Use | Licence |
| --- | --- | --- |
| `EBGaramond-Regular.otf`, `-Italic.otf`, `-Medium.otf`, `-SemiBold.otf`, `-SemiBoldItalic.otf` | body text, display, small caps | SIL OFL 1.1, `OFL-EBGaramond.txt` |
| `EBGaramond-Initials.otf` | chapter drop caps | SIL OFL 1.1, `OFL-EBGaramond.txt` |
| `LibertinusSerif-Regular.otf` | fallback for glyphs EB Garamond lacks | SIL OFL 1.1, `OFL-Libertinus.txt` |
| `DejaVuSerif.ttf` | second fallback | Bitstream Vera / DejaVu licence, `LICENSE-DejaVu.txt` |

To change a face, replace the file here and rebuild every book; page counts may move, which moves the
covers. The ebook (`fine-ebook.sty`) embeds no fonts and does not use this folder.
