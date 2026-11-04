"""A layout's safe areas and barcode box against KDP's published minimums."""

from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class LayoutCheck:
    """Reports each rule a layout breaks."""

    def run(self, layout: CoverLayout) -> list[str]:
        """Return layout problems; an empty list means the layout is within KDP's limits."""
        problems: list[str] = []
        if layout.kind == "paperback":
            self._paperback(layout, problems)
        if layout.kind == "hardcover":
            self._hardcover(layout, problems)
        return problems

    def _need(self, layout: CoverLayout, problems: list[str], ok: bool, what: str) -> None:
        if not ok:
            problems.append(f"[{layout.kind}] layout: {what}")

    def _paperback(self, L: CoverLayout, problems: list[str]) -> None:
        assert_ = self._need
        back, spine, barcode = L.back, L.spine, L.barcode
        if back is None or spine is None or barcode is None or L.back_safe is None:
            raise ValueError("a paperback layout needs back, spine, and barcode boxes")
        for name, safe, panel in (("front", L.front_safe, L.front), ("back", L.back_safe, back)):
            assert_(
                L,
                problems,
                safe.x0 >= panel.x0 + 0.125
                and safe.x1 <= panel.x1 - 0.125
                and safe.y0 >= panel.y0 + 0.125
                and safe.y1 <= panel.y1 - 0.125,
                f"{name} text must sit 0.125 in inside the trim",
            )
        if L.spine_safe is not None:
            assert_(
                L,
                problems,
                L.spine_safe.x0 >= spine.x0 + 0.0625 and L.spine_safe.x1 <= spine.x1 - 0.0625,
                "spine text needs 0.0625 in on each side",
            )
        assert_(
            L,
            problems,
            barcode.x0 >= back.x0 and barcode.x1 <= back.x1 and barcode.y1 <= back.y1,
            "barcode box must sit on the back cover",
        )

    def _hardcover(self, L: CoverLayout, problems: list[str]) -> None:
        assert_ = self._need
        back, spine, barcode = L.back, L.spine, L.barcode
        if back is None or spine is None or barcode is None or L.back_safe is None:
            raise ValueError("a hardcover layout needs back, spine, and barcode boxes")
        assert_(
            L,
            problems,
            L.front_safe.x0 >= L.front.x0 + Kdp.HC_HINGE
            and L.back_safe.x1 <= back.x1 - Kdp.HC_HINGE,
            "text must stay out of the 10 mm hinge",
        )
        for name, safe, board in (("front", L.front_safe, L.front), ("back", L.back_safe, back)):
            assert_(
                L,
                problems,
                safe.y0 >= board.y0 + 0.125
                and safe.y1 <= board.y1 - 0.125
                and safe.x0 >= board.x0 + 0.125
                and safe.x1 <= board.x1 - 0.125,
                f"{name} text must sit 0.125 in inside the board edge",
            )
        if L.spine_safe is not None:
            assert_(
                L,
                problems,
                L.spine_safe.x0 >= spine.x0 + 0.0625 and L.spine_safe.x1 <= spine.x1 - 0.0625,
                "spine text needs 0.0625 in on each side",
            )
        assert_(
            L,
            problems,
            L.height - barcode.y1 >= 0.76 - 1e-9,
            "barcode must sit 0.76 in above the bottom edge",
        )
        assert_(
            L,
            problems,
            barcode.x1 <= back.x1 - Kdp.HC_HINGE - 0.25 + 1e-9,
            "barcode must sit 0.25 in from the hinge",
        )
