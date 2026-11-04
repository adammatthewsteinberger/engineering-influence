"""Reads an EPUB into EpubContents."""

import zipfile
from pathlib import Path

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.epub.xhtml_patterns import XhtmlPatterns


class EpubArchive:
    """Decodes the XHTML, OPF, NCX, and CSS members and locates the package parts."""

    def read(self, path: Path) -> EpubContents:
        """Load the archive at path."""
        with zipfile.ZipFile(path) as archive:
            first = archive.infolist()[0]
            mimetype_ok = first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
            names = archive.namelist()
            docs = {
                n: archive.read(n).decode("utf-8")
                for n in names
                if n.endswith((".xhtml", ".opf", ".ncx"))
            }
            styles = {n: archive.read(n).decode("utf-8") for n in names if n.endswith(".css")}
        opf_name = next((n for n in docs if n.endswith(".opf")), "")
        opf_text = docs.get(opf_name, "")
        nav_match = XhtmlPatterns.NAV_ITEM.search(opf_text)
        base = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
        nav_href = nav_match.group(1) if nav_match else ""
        nav_name = base + nav_href if nav_match else ""
        return EpubContents(
            path=path,
            mimetype_ok=mimetype_ok,
            docs=docs,
            styles=styles,
            base=base,
            opf_name=opf_name,
            opf_text=opf_text,
            nav_href=nav_href,
            nav_name=nav_name,
            nav=docs.get(nav_name, ""),
            ncx_name=next((n for n in docs if n.endswith(".ncx")), ""),
        )
