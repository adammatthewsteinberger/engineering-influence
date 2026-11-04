"""An axis-aligned rectangle in inches."""

from dataclasses import dataclass


@dataclass
class Box:
    """Left, top, right, bottom edges."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        """Width."""
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        """Height."""
        return self.y1 - self.y0

    def inset(
        self,
        left: float,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
    ) -> "Box":
        """Shrink by the given amounts; omitted sides repeat the previous one."""
        top = left if top is None else top
        right = left if right is None else right
        bottom = top if bottom is None else bottom
        return Box(self.x0 + left, self.y0 + top, self.x1 - right, self.y1 - bottom)
