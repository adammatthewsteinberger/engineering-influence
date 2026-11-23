# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The listing a person pastes into KDP, as the markdown that is written next to the files."""

from dataclasses import dataclass

from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.models.interfaces.kdp_listing_interface import KdpListingInterface


@dataclass(frozen=True, slots=True)
class KdpListing(KdpListingInterface):
    """The listing text. Every field is already held to the limits ``BookMetadata`` enforces."""

    metadata: BookMetadata

    def render(self, files: tuple[tuple[str, str, int, str], ...]) -> str:
        """Markdown with the listing fields, then the files in the bundle: kind, name, bytes and SHA-256."""
        m = self.metadata
        lines = [
            f"# {m.title}",
            "",
            f"Subtitle: {m.subtitle}",
            "",
            "## Description",
            "",
            m.description,
            "",
        ]
        lines += ["## Keywords", ""] + [f"- {keyword}" for keyword in m.keywords] + [""]
        lines += ["## Categories", ""] + [f"- {category}" for category in m.categories] + [""]
        lines += ["## Files", "", "| kind | file | bytes | sha256 |", "| --- | --- | ---: | --- |"]
        lines += [f"| {kind} | {name} | {size} | {digest} |" for kind, name, size, digest in files]
        lines += [
            "",
            "This folder was made by `ei book package`. KDP has no publishing API: upload these files and paste",
            "the listing above yourself, then check the manifest's hashes against the files you uploaded.",
            "",
        ]
        return "\n".join(lines)
