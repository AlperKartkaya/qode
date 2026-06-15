from __future__ import annotations

import html
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DocxBlock:
    kind: str
    text: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    level: int = 1


def write_docx(blocks: tuple[DocxBlock, ...], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _rels_xml())
        zf.writestr("docProps/core.xml", _core_xml())
        zf.writestr("docProps/app.xml", _app_xml())
        zf.writestr("word/styles.xml", _styles_xml())
        zf.writestr("word/document.xml", _document_xml(blocks))
    return target


def extract_docx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    xml = xml.replace("</w:p>", "\n")
    xml = xml.replace("</w:tc>", "\t")
    text = []
    in_tag = False
    current = []
    for char in xml:
        if char == "<":
            in_tag = True
            if current:
                text.append("".join(current))
                current = []
        elif char == ">":
            in_tag = False
        elif not in_tag:
            current.append(char)
    if current:
        text.append("".join(current))
    return html.unescape("".join(text))


def _document_xml(blocks: tuple[DocxBlock, ...]) -> str:
    body = "".join(_block_xml(block) for block in blocks)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}{_section_xml()}</w:body></w:document>"
    )


def _block_xml(block: DocxBlock) -> str:
    if block.kind == "page_break":
        return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    if block.kind == "heading":
        style = "Heading1" if block.level <= 1 else "Heading2"
        return _paragraph_xml(block.text, style)
    if block.kind == "title":
        return _paragraph_xml(block.text, "Title")
    if block.kind == "subtitle":
        return _paragraph_xml(block.text, "Subtitle")
    if block.kind == "bullet":
        return _paragraph_xml("• " + block.text, "Normal")
    if block.kind == "table":
        return _table_xml(block.rows)
    return _paragraph_xml(block.text, "Normal")


def _paragraph_xml(text: str, style: str) -> str:
    runs = "".join(_run_xml(part) for part in text.split("\n"))
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{runs}</w:p>'


def _run_xml(text: str) -> str:
    return f"<w:r><w:t xml:space=\"preserve\">{html.escape(text)}</w:t></w:r>"


def _table_xml(rows: tuple[tuple[str, ...], ...]) -> str:
    if not rows:
        return ""
    row_xml = []
    for row in rows:
        cells = "".join(
            "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
            f"{_paragraph_xml(cell, 'Normal')}</w:tc>"
            for cell in row
        )
        row_xml.append(f"<w:tr>{cells}</w:tr>")
    borders = (
        "<w:tblPr><w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        "</w:tblBorders></w:tblPr>"
    )
    return f"<w:tbl>{borders}{''.join(row_xml)}</w:tbl>"


def _section_xml() -> str:
    return (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1588" w:right="1418" w:bottom="1418" w:left="1418" '
        'w:header="709" w:footer="283" w:gutter="0"/>'
        "</w:sectPr>"
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def _rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _core_xml() -> str:
    now = datetime.now(timezone.utc).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>Akıllı Yol Güvenliği Final Tasarım Raporu</dc:title>'
        '<dc:creator>smart_road_safety report generator</dc:creator>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>smart_road_safety</Application>'
        "</Properties>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        '<w:sz w:val="24"/></w:rPr><w:pPr><w:spacing w:line="276" w:lineRule="auto"/>'
        '<w:jc w:val="both"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title">'
        '<w:name w:val="Title"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial Black" w:hAnsi="Arial Black"/>'
        '<w:b/><w:sz w:val="32"/></w:rPr><w:pPr><w:jc w:val="center"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Subtitle">'
        '<w:name w:val="Subtitle"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        '<w:sz w:val="24"/></w:rPr><w:pPr><w:jc w:val="center"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial Black" w:hAnsi="Arial Black"/>'
        '<w:b/><w:sz w:val="28"/></w:rPr><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial Black" w:hAnsi="Arial Black"/>'
        '<w:b/><w:sz w:val="26"/></w:rPr><w:pPr><w:spacing w:before="180" w:after="90"/></w:pPr></w:style>'
        "</w:styles>"
    )
