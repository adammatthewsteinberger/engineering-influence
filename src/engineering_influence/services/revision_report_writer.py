# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes the revision log and the source mapping as Markdown tables, in the locked script's order."""

from engineering_influence.models.scene_revision import SceneRevision
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.services.interfaces.revision_report_writer_interface import (
    RevisionReportWriterInterface,
)


class RevisionReportWriter(RevisionReportWriterInterface):
    """Omitted scenes stay in both tables, with their number and card, so the tables run through every number the
    lock has given. A scene the lock keeps and no revision describes is refused: the report would have a gap."""

    def revision_log(self, lock: ShootingLock, scenes: tuple[SceneRevision, ...]) -> str:
        by_card = self._by_card(lock, scenes)
        rows = [
            "| Scene | Card | Status | Draft words | Revised words |",
            "| --- | --- | --- | --- | --- |",
        ]
        for entry in lock.entries:
            card = f"S{entry.card:02d}"
            if entry.omitted:
                rows.append(f"| {entry.label} | {card} | omitted | | |")
            else:
                scene = by_card[entry.card]
                rows.append(
                    f"| {entry.label} | {card} | {scene.status()} | {scene.draft_words} | {scene.revised_words} |"
                )
        return self._document("Revision log", rows)

    def source_mapping(self, lock: ShootingLock, scenes: tuple[SceneRevision, ...]) -> str:
        by_card = self._by_card(lock, scenes)
        rows = ["| Scene | Card | Beat | Sources |", "| --- | --- | --- | --- |"]
        for entry in lock.entries:
            card = f"S{entry.card:02d}"
            if entry.omitted:
                rows.append(f"| {entry.label} | {card} | omitted | |")
            else:
                scene = by_card[entry.card]
                sources = ", ".join(f"{number:03d}" for number in scene.card.sources)
                rows.append(f"| {entry.label} | {card} | {scene.card.beat} | {sources} |")
        return self._document("Source mapping", rows)

    @staticmethod
    def _by_card(lock: ShootingLock, scenes: tuple[SceneRevision, ...]) -> dict[int, SceneRevision]:
        by_card = {scene.card.number: scene for scene in scenes}
        missing = [
            entry.card for entry in lock.entries if not entry.omitted and entry.card not in by_card
        ]
        if missing:
            raise ValueError(f"no revision is recorded for scene cards {missing}")
        return by_card

    @staticmethod
    def _document(title: str, rows: list[str]) -> str:
        return "\n".join([f"# {title}", "", *rows]) + "\n"
