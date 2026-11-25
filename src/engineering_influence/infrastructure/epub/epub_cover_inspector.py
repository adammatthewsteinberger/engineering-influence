# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Decodes the cover image in a built EPUB and judges it against the Kindle rules."""

import io
import zipfile

from PIL import Image

from engineering_influence.interfaces.epub_cover_inspector_interface import (
    EpubCoverInspectorInterface,
)
from engineering_influence.models.epub.cover_declaration import CoverDeclaration
from engineering_influence.models.epub.epub_contents import EpubContents


class EpubCoverInspector(EpubCoverInspectorInterface):
    """Opens the archive and the image with zipfile and Pillow."""

    def problems(self, contents: EpubContents, href: str) -> list[str]:
        """Return the problems with the image the OPF declares at href."""
        problems: list[str] = []
        try:
            with (
                zipfile.ZipFile(contents.path) as archive,
                Image.open(io.BytesIO(archive.read(contents.base + href))) as image,
            ):
                image.load()
                width, height = image.size
                if image.format != "JPEG" or image.mode != "RGB":
                    problems.append(
                        f"the cover image is {image.format} {image.mode}; expected an RGB JPEG"
                    )
                if width < CoverDeclaration.MIN_PX[0] or height < CoverDeclaration.MIN_PX[1]:
                    problems.append(
                        f"the cover image is {width} x {height} px; KDP wants at least "
                        f"{CoverDeclaration.MIN_PX[0]} x {CoverDeclaration.MIN_PX[1]}"
                    )
        except KeyError:
            problems.append(f"the cover image {href} is missing from the EPUB")
        except Exception as error:  # noqa: BLE001 - any decode failure fails KDP review
            problems.append(f"the cover image does not decode: {error}")
        return problems
