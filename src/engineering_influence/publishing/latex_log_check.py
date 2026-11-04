"""Reads a LaTeX log for missing glyphs and overfull lines."""

import re


class LatexLogCheck:
    """Flags typesetting defects the PDF itself cannot reveal."""

    def run(self, log: str) -> list[str]:
        """Return a problem per missing glyph and one for overfull lines over 1pt."""
        problems = [
            f"missing glyph {glyph}"
            for glyph in sorted(
                set(re.findall(r"Missing character: There is no (\S+ \(U\+[0-9A-F]+\))", log))
            )
        ]
        overfull = [float(x) for x in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)]
        bad = [width for width in overfull if width > 1.0]
        if bad:
            problems.append(f"{len(bad)} overfull lines (worst {max(bad):.1f}pt)")
        return problems
