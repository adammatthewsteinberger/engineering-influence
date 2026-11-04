"""Amazon KDP print geometry constants and gutter lookup."""


class KdpGeometry:
    """Trim size, margins, and page-count-dependent gutter for a 6 x 9 in interior."""

    POINTS_PER_INCH = 72.0
    TRIM = (6 * POINTS_PER_INCH, 9 * POINTS_PER_INCH)
    GUTTER_TABLE = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
    OUTER_MIN = 0.25 * POINTS_PER_INCH
    TOLERANCE = 0.5

    def gutter_inches(self, pages: int) -> float:
        """Return the minimum gutter in inches for a book of the given page count."""
        for limit, inches in self.GUTTER_TABLE:
            if pages <= limit:
                return inches
        raise ValueError(f"KDP does not print {pages}-page paperbacks")
