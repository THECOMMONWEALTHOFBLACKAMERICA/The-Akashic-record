from __future__ import annotations

import io
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import PurePosixPath

from bs4 import BeautifulSoup

_CONTAINER = "META-INF/container.xml"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_epub(data: bytes) -> tuple[dict, list[tuple[int | None, str]]]:
    """Extract metadata and ordered readable text from an EPUB archive.

    The parser intentionally avoids executing scripts or loading remote resources.
    It follows container.xml -> OPF manifest/spine and converts XHTML/HTML chapters
    to plain text suitable for T.A.R. chunking and retrieval.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        if _CONTAINER not in names:
            raise ValueError("Invalid EPUB: META-INF/container.xml missing")

        container = ET.fromstring(zf.read(_CONTAINER))
        rootfile = next((e for e in container.iter() if _local_name(e.tag) == "rootfile"), None)
        if rootfile is None or not rootfile.attrib.get("full-path"):
            raise ValueError("Invalid EPUB: package document missing")
        opf_path = rootfile.attrib["full-path"]
        if opf_path not in names:
            raise ValueError("Invalid EPUB: OPF file not found")

        opf = ET.fromstring(zf.read(opf_path))
        opf_dir = posixpath.dirname(opf_path)

        metadata: dict[str, str] = {}
        for e in opf.iter():
            key = _local_name(e.tag).lower()
            if key in {"title", "creator", "language", "publisher", "description", "identifier", "date"} and e.text:
                metadata.setdefault(key, unescape(e.text.strip()))

        manifest: dict[str, tuple[str, str]] = {}
        spine: list[str] = []
        for e in opf.iter():
            name = _local_name(e.tag)
            if name == "item":
                item_id = e.attrib.get("id")
                href = e.attrib.get("href")
                if item_id and href:
                    manifest[item_id] = (href, e.attrib.get("media-type", ""))
            elif name == "itemref" and e.attrib.get("idref"):
                spine.append(e.attrib["idref"])

        chapters: list[tuple[int | None, str]] = []
        ordinal = 0
        for item_id in spine:
            item = manifest.get(item_id)
            if not item:
                continue
            href, media_type = item
            if media_type not in {"application/xhtml+xml", "text/html", "application/xml"} and not href.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            path = posixpath.normpath(posixpath.join(opf_dir, href))
            if path.startswith("../") or path not in names:
                continue
            raw = zf.read(path)
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
            if text:
                ordinal += 1
                chapters.append((ordinal, text))

        if not chapters:
            # Fallback for malformed EPUBs with no usable spine.
            for name in sorted(names):
                if not name.lower().endswith((".xhtml", ".html", ".htm")):
                    continue
                soup = BeautifulSoup(zf.read(name), "html.parser")
                for tag in soup(["script", "style", "noscript", "svg"]):
                    tag.decompose()
                text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
                if text:
                    ordinal += 1
                    chapters.append((ordinal, text))

        if not chapters:
            raise ValueError("EPUB contains no readable chapters")
        metadata["chapter_count"] = str(len(chapters))
        return metadata, chapters
