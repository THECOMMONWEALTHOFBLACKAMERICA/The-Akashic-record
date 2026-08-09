import io
import zipfile

from backend.app.epub import parse_epub


def _sample_epub() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version='1.0'?>
            <container xmlns='urn:oasis:names:tc:opendocument:xmlns:container' version='1.0'>
              <rootfiles><rootfile full-path='OEBPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles>
            </container>""",
        )
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version='1.0' encoding='utf-8'?>
            <package xmlns='http://www.idpf.org/2007/opf' version='3.0'>
              <metadata xmlns:dc='http://purl.org/dc/elements/1.1/'>
                <dc:title>Archive Book</dc:title><dc:creator>Historian</dc:creator><dc:language>en</dc:language>
              </metadata>
              <manifest><item id='c1' href='chapter1.xhtml' media-type='application/xhtml+xml'/></manifest>
              <spine><itemref idref='c1'/></spine>
            </package>""",
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            "<html xmlns='http://www.w3.org/1999/xhtml'><body><h1>Chapter One</h1><p>Primary source evidence.</p><script>bad()</script></body></html>",
        )
    return buf.getvalue()


def test_parse_epub_metadata_and_text():
    metadata, chapters = parse_epub(_sample_epub())
    assert metadata["title"] == "Archive Book"
    assert metadata["creator"] == "Historian"
    assert metadata["chapter_count"] == "1"
    assert chapters[0][0] == 1
    assert "Primary source evidence" in chapters[0][1]
    assert "bad()" not in chapters[0][1]
