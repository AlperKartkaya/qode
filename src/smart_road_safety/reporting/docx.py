from __future__ import annotations

import html
import struct
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EMU_PER_DXA = 635
CONTENT_WIDTH_DXA = 9070
MAX_IMAGE_WIDTH_DXA = 8500


@dataclass(frozen=True)
class DocxBlock:
    kind: str
    text: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    level: int = 1


def write_docx(blocks: tuple[DocxBlock, ...], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image_map = _build_image_map(blocks)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _rels_xml())
        zf.writestr("docProps/core.xml", _core_xml())
        zf.writestr("docProps/app.xml", _app_xml())
        zf.writestr("word/styles.xml", _styles_xml())
        zf.writestr("word/_rels/document.xml.rels", _document_rels_xml(image_map))
        zf.writestr("word/document.xml", _document_xml(blocks, image_map))
        for path_text, image_info in image_map.items():
            zf.write(path_text, f"word/media/{image_info['target']}")
    return target


def extract_docx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    xml = xml.replace("<w:br/>", "\n")
    xml = xml.replace('<w:br w:type="page"/>', "\n")
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


def _build_image_map(blocks: tuple[DocxBlock, ...]) -> dict[str, dict[str, str]]:
    image_map: dict[str, dict[str, str]] = {}
    for block in blocks:
        if block.kind != "image" or not block.text:
            continue
        path = Path(block.text)
        if not path.exists():
            continue
        path_text = str(path)
        if path_text in image_map:
            continue
        index = len(image_map) + 1
        image_map[path_text] = {
            "rid": f"rId{index}",
            "target": f"image{index}{path.suffix.lower() or '.png'}",
        }
    return image_map


def _document_xml(blocks: tuple[DocxBlock, ...], image_map: dict[str, dict[str, str]]) -> str:
    body = "".join(_block_xml(block, image_map) for block in blocks)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f"<w:body>{body}{_section_xml()}</w:body></w:document>"
    )


def _block_xml(block: DocxBlock, image_map: dict[str, dict[str, str]]) -> str:
    if block.kind == "page_break":
        return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    if block.kind == "heading":
        return _paragraph_xml(block.text, "Heading")
    if block.kind == "title":
        return _paragraph_xml(block.text, "Title")
    if block.kind == "subtitle":
        return _paragraph_xml(block.text, "Subtitle")
    if block.kind == "caption":
        return _paragraph_xml(block.text, "Caption")
    if block.kind == "image":
        return _image_xml(block.text, image_map)
    if block.kind == "bullet":
        return _paragraph_xml("• " + block.text, "Normal")
    if block.kind == "table":
        return _table_xml(block.rows)
    return _paragraph_xml(block.text, "Normal")


def _paragraph_xml(text: str, style: str) -> str:
    parts = text.split("\n")
    runs: list[str] = []
    for index, part in enumerate(parts):
        if index:
            runs.append('<w:r><w:br/></w:r>')
        runs.append(_run_xml(part))
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{"".join(runs)}</w:p>'


def _run_xml(text: str) -> str:
    return f"<w:r><w:t xml:space=\"preserve\">{html.escape(text)}</w:t></w:r>"


def _image_xml(path_text: str, image_map: dict[str, dict[str, str]]) -> str:
    info = image_map.get(path_text)
    if info is None:
        return _paragraph_xml(f"[Görsel bulunamadı: {path_text}]", "Caption")
    width_px, height_px = _png_dimensions(Path(path_text))
    width_dxa = MAX_IMAGE_WIDTH_DXA
    height_dxa = int(width_dxa * height_px / width_px)
    if height_dxa > 6500:
        height_dxa = 6500
        width_dxa = int(height_dxa * width_px / height_px)
    cx = width_dxa * EMU_PER_DXA
    cy = height_dxa * EMU_PER_DXA
    rid = info["rid"]
    name = html.escape(Path(path_text).name)
    return (
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="120"/></w:pPr><w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{abs(hash(path_text)) % 100000}" name="{name}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr>'
        f'<pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/>'
        '</pic:nvPicPr><pic:blipFill>'
        f'<a:blip r:embed="{rid}"/>'
        '<a:stretch><a:fillRect/></a:stretch>'
        '</pic:blipFill><pic:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '</pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>'
    )


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        signature = file.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Only PNG images are supported in DOCX reports: {path}")
        length = file.read(4)
        chunk = file.read(4)
        if chunk != b"IHDR":
            raise ValueError(f"Invalid PNG IHDR chunk: {path}")
        data = file.read(8)
    width, height = struct.unpack(">II", data)
    return width, height


def _table_xml(rows: tuple[tuple[str, ...], ...]) -> str:
    if not rows:
        return ""
    max_cols = max(len(row) for row in rows)
    if max_cols == 0:
        return ""
    cell_width = max(1100, CONTENT_WIDTH_DXA // max_cols)
    grid = "".join(f'<w:gridCol w:w="{cell_width}"/>' for _ in range(max_cols))
    row_xml = []
    for row_index, row in enumerate(rows):
        cells = []
        for column_index in range(max_cols):
            cell = row[column_index] if column_index < len(row) else ""
            fill = '<w:shd w:fill="D9EAF7"/>' if row_index == 0 else ""
            cells.append(
                "<w:tc><w:tcPr>"
                f'<w:tcW w:w="{cell_width}" w:type="dxa"/>{fill}'
                "</w:tcPr>"
                f"{_paragraph_xml(cell, 'TableHeader' if row_index == 0 else 'Normal')}"
                "</w:tc>"
            )
        row_xml.append(f"<w:tr>{''.join(cells)}</w:tr>")
    borders = (
        f'<w:tblPr><w:tblW w:w="{CONTENT_WIDTH_DXA}" w:type="dxa"/>'
        '<w:tblInd w:w="0" w:type="dxa"/>'
        '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tblCellMar>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="666666"/>'
        "</w:tblBorders></w:tblPr>"
    )
    return f"<w:tbl>{borders}<w:tblGrid>{grid}</w:tblGrid>{''.join(row_xml)}</w:tbl>"


def _section_xml() -> str:
    return (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1588" w:right="1418" w:bottom="1418" w:left="1418" '
        'w:header="709" w:footer="709" w:gutter="0"/>'
        "</w:sectPr>"
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
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


def _document_rels_xml(image_map: dict[str, dict[str, str]]) -> str:
    relationships = []
    for info in image_map.values():
        relationships.append(
            f'<Relationship Id="{info["rid"]}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{info["target"]}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(relationships)
        + "</Relationships>"
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
        '<w:sz w:val="24"/><w:color w:val="111111"/></w:rPr>'
        '<w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/>'
        '<w:jc w:val="both"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title">'
        '<w:name w:val="Title"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial Black" w:hAnsi="Arial Black"/>'
        '<w:b/><w:sz w:val="28"/><w:color w:val="0B2545"/></w:rPr>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Subtitle">'
        '<w:name w:val="Subtitle"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        '<w:b/><w:sz w:val="24"/><w:color w:val="44546A"/></w:rPr>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:after="80" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading">'
        '<w:name w:val="heading"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial Black" w:hAnsi="Arial Black"/>'
        '<w:b/><w:sz w:val="28"/><w:color w:val="4C5F78"/></w:rPr>'
        '<w:pPr><w:spacing w:before="240" w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Caption">'
        '<w:name w:val="Caption"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        '<w:i/><w:sz w:val="20"/><w:color w:val="5F6B7A"/></w:rPr>'
        '<w:pPr><w:spacing w:before="60" w:after="60" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="TableHeader">'
        '<w:name w:val="Table Header"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        '<w:b/><w:sz w:val="22"/><w:color w:val="0B2545"/></w:rPr>'
        '<w:pPr><w:spacing w:after="40" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
        "</w:styles>"
    )
