"""The internal cover image is declared, present, a large RGB JPEG, and not shown on a page."""

import io
import re
import zipfile

from PIL import Image

from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.epub_contents import EpubContents


class CoverCheck:
    """The Kindle Publishing Guidelines require an internal cover declared in the OPF."""

    def run(self, contents: EpubContents) -> list[str]:
        """Return problems with the cover declaration and image."""
        problems: list[str] = []
        opf_text = contents.opf_text
        item = re.search(r"<item\b(?=[^>]*properties=.[^'\"]*cover-image)[^>]*>", opf_text)
        if not item:
            problems.append('the OPF declares no cover image (properties="cover-image")')
        else:
            problems += self._image_problems(contents, item.group(0))
        pages = "".join(v for k, v in contents.docs.items() if k.endswith(".xhtml"))
        if re.search(r"<(?:img|svg)\b", pages):
            problems.append(
                "an XHTML page shows an image; KDP warns that an HTML cover page "
                "duplicates the cover"
            )
        return problems

    def _image_problems(self, contents: EpubContents, item: str) -> list[str]:
        problems: list[str] = []
        href_match = re.search(r"href=.([^'\"]+)", item)
        id_match = re.search(r"\bid=.([^'\"]+)", item)
        href = href_match.group(1) if href_match else ""
        cover_id = id_match.group(1) if id_match else ""
        if not re.search(r"media-type=.image/jpeg", item):
            problems.append("the cover image is not declared as image/jpeg")
        if not re.search(rf'<meta name="cover" content="{re.escape(cover_id)}"', contents.opf_text):
            problems.append('the OPF has no <meta name="cover"> pointing at the cover image')
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
                if width < CoverImage.MIN_PX[0] or height < CoverImage.MIN_PX[1]:
                    problems.append(
                        f"the cover image is {width} x {height} px; KDP wants at least "
                        f"{CoverImage.MIN_PX[0]} x {CoverImage.MIN_PX[1]}"
                    )
        except KeyError:
            problems.append(f"the cover image {href} is missing from the EPUB")
        except Exception as error:  # noqa: BLE001 - any decode failure fails KDP review
            problems.append(f"the cover image does not decode: {error}")
        return problems
