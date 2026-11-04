"""Checks that every table-of-contents entry points at the page that prints it."""

import re

from engineering_influence.publishing.text_normalizer import TextNormalizer


class ContentsCheck:
    """Compares Contents entries with the folios printed on the pages themselves."""

    def run(
        self, texts: list[str], folios: list[str | None], title: str
    ) -> tuple[list[str], int | None]:
        """Return (problems, entries checked); entries is None when no Contents page exists."""
        start = next(
            (i for i, text in enumerate(texts) if text.strip().startswith("Contents")), None
        )
        if start is None:
            return ["no Contents page found"], None
        problems: list[str] = []
        entries = self._entries(texts, folios, title, start)
        if not entries:
            problems.append("could not read any table-of-contents entries")
        normalizer = TextNormalizer()
        for entry_title, label in entries:
            index = self._physical(folios, label)
            if index is None:
                problems.append(
                    f"ToC entry {entry_title!r} points at page {label}, which does not exist"
                )
                continue
            page_text = normalizer.normalize(texts[index])
            want = normalizer.normalize(re.sub(r"^\d+\s*", "", entry_title))
            if want[:32] not in page_text[:400]:
                problems.append(
                    f"ToC entry {entry_title!r} says page {label}, but that page "
                    f"(physical {index + 1}) does not start it"
                )
        return problems, len(entries)

    def _entries(
        self, texts: list[str], folios: list[str | None], title: str, start: int
    ) -> list[tuple[str, str]]:
        normalizer = TextNormalizer()
        heads = ("contents", normalizer.normalize(title))
        entries: list[tuple[str, str]] = []
        i = start
        while i < len(texts):
            lines = texts[i].split("\n")
            if i > start and not any(re.search(r"\s(\d+|[ivxlc]+)$", line) for line in lines[1:]):
                break
            folio = folios[i]
            if i > start and folio and folio.isdigit():
                break
            pending = ""
            for raw in lines:
                line = raw.strip()
                if not line or line == "Contents":
                    continue
                # Running heads are not entries, even when the title ends in a letter like "l".
                if any(
                    re.fullmatch(
                        rf"[ivxlc\d]*{re.escape(head)}[ivxlc\d]*", normalizer.normalize(line)
                    )
                    for head in heads
                ):
                    continue
                match = re.match(r"(.*?)\s+(\d+|[ivxlc]+)$", line)
                if match and not re.fullmatch(r"[ivxlc\d]+", line):
                    entries.append(((pending + " " + match.group(1)).strip(), match.group(2)))
                    pending = ""
                elif not re.fullmatch(r"[ivxlc\d]*", normalizer.normalize(line)):
                    pending = (pending + " " + line).strip()
            i += 1
        return entries

    def _physical(self, folios: list[str | None], label: str) -> int | None:
        for index, folio in enumerate(folios):
            if folio == label:
                return index
        if label.isdigit():  # parts print no folio: infer from the nearest numbered page after
            target = int(label)
            for index, folio in enumerate(folios):
                if folio and folio.isdigit() and int(folio) > target:
                    candidate = index - (int(folio) - target)
                    if candidate >= 0 and folios[candidate] is None:
                        return candidate
                    break
        return None
