# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Amazon KDP print geometry constants and gutter lookup."""

from engineering_influence.services.publishing.interfaces.kdp_geometry_interface import (
    KdpGeometryInterface,
)


class KdpGeometry(KdpGeometryInterface):
    """Margins and the page-count-dependent gutter, which KDP sets the same for every trim size."""

    POINTS_PER_INCH = 72.0
    GUTTER_TABLE = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
    OUTER_MIN = 0.25 * POINTS_PER_INCH
    TOLERANCE = 0.5

    def gutter_inches(self, pages: int) -> float:
        """Return the minimum gutter in inches for a book of the given page count."""
        for limit, inches in self.GUTTER_TABLE:
            if pages <= limit:
                return inches
        raise ValueError(f"KDP does not print {pages}-page paperbacks")
