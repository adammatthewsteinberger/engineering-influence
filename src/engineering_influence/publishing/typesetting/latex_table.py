"""Markdown tables to a tabularx environment."""


class LatexTable:
    """Renders rows of already-rendered cells; the first row is the header."""

    def render(self, rows: list[list[str]]) -> str:
        """Return the LaTeX table, or an empty string for no rows."""
        if not rows:
            return ""
        cols = max(len(row) for row in rows)
        spec = "@{}" + ">{\\raggedright\\arraybackslash}X" * cols + "@{}"
        lines = [
            "\n\\begin{center}\\small",
            f"\\begin{{tabularx}}{{\\textwidth}}{{{spec}}}",
            r"\toprule",
        ]
        for number, row in enumerate(rows):
            row = row + [""] * (cols - len(row))
            cells = [f"\\textbf{{{cell}}}" if number == 0 else cell for cell in row]
            lines.append(" & ".join(cells) + r" \\")
            if number == 0:
                lines.append(r"\midrule")
        lines += [r"\bottomrule", r"\end{tabularx}", r"\end{center}"]
        return "\n".join(lines) + "\n"
