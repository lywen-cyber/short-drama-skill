#!/usr/bin/env python3
"""把项目 Markdown 源稿导出为宁式排版的 Word。

宁式（与 references/正文格式.md 一致，未另给格式时的默认）：
- 动作和画面用 △，与后面的文字同一段，不单独一行只放一个三角；
- 对白另起一行，一般不与 △ 混在同一段；
- 场头、人物行、△ 段落、对白都按源稿分段写出，不临场改写正文。

排版固定为：A4；左右页边距 1.25 英寸、上下 1 英寸；
正文 10.5 磅宋体（西文 Times New Roman）、两端对齐；
可选剧名用 16 磅黑体（西文 Arial）、加粗、居中。

用法：
  python scripts/export_docx.py <项目目录或分集文件> -o 剧名.docx
  python scripts/export_docx.py examples/示例项目 --title 示例项目 -o /tmp/示例项目.docx

默认扫描 `episodes/第NN集.md`，并兼容旧的 `ep*.txt` 和根目录 `第N集.md`。
交稿前的字数以源稿为准，请用 scripts/count.py 统计 Markdown，本脚本不负责字数。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from count import iter_episode_files  # noqa: E402

ASCII_BODY = "Times New Roman"
EAST_BODY = "宋体"
ASCII_TITLE = "Arial"
EAST_TITLE = "黑体"


def _set_run_font(run, *, east: str, ascii_font: str, size_pt: float, bold: bool | None = None) -> None:
    run.font.size = Pt(size_pt)
    run.font.name = ascii_font
    if bold is not None:
        run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:cs"), ascii_font)


def _set_style_font(style, *, east: str, ascii_font: str, size_pt: float, bold: bool | None = None, justify: bool = False) -> None:
    font = style.font
    font.name = ascii_font
    font.size = Pt(size_pt)
    if bold is not None:
        font.bold = bold
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:cs"), ascii_font)
    if justify:
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)


def _setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1.25)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)

    rPrDefault = doc.styles.element.find(qn("w:docDefaults"))
    if rPrDefault is not None:
        rPr = rPrDefault.find(qn("w:rPrDefault"))
        if rPr is not None:
            inner = rPr.find(qn("w:rPr"))
            if inner is not None:
                rFonts = inner.find(qn("w:rFonts"))
                if rFonts is None:
                    rFonts = inner.makeelement(qn("w:rFonts"), {})
                    inner.insert(0, rFonts)
                rFonts.set(qn("w:ascii"), ASCII_BODY)
                rFonts.set(qn("w:hAnsi"), ASCII_BODY)
                rFonts.set(qn("w:eastAsia"), EAST_BODY)
                rFonts.set(qn("w:cs"), ASCII_BODY)

    _set_style_font(doc.styles["Normal"], east=EAST_BODY, ascii_font=ASCII_BODY, size_pt=10.5, justify=True)
    return doc


def iter_source_lines(text: str) -> list[str]:
    """从源稿取出要写入 Word 的行：保留正文分段，去掉 Markdown 壳。"""
    lines = text.splitlines()
    out: list[str] = []
    in_frontmatter = False
    for i, raw in enumerate(lines):
        s = raw.rstrip("\n")
        if i == 0 and s.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if s.strip() == "---":
                in_frontmatter = False
            continue
        stripped = s.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            continue
        out.append(s.rstrip())
    # 首尾空白去掉，中间连续空行压成一行
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    collapsed: list[str] = []
    blank = False
    for line in out:
        if not line.strip():
            if not blank:
                collapsed.append("")
            blank = True
        else:
            collapsed.append(line.strip())
            blank = False
    return collapsed


def add_body_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if text:
        run = p.add_run(text)
        _set_run_font(run, east=EAST_BODY, ascii_font=ASCII_BODY, size_pt=10.5)
    else:
        # 保留空段作为场与场之间的间隔
        run = p.add_run("")
        _set_run_font(run, east=EAST_BODY, ascii_font=ASCII_BODY, size_pt=10.5)


def add_title(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(13)
    run = p.add_run(title)
    _set_run_font(run, east=EAST_TITLE, ascii_font=ASCII_TITLE, size_pt=16, bold=True)


def export_docx(source: Path, output: Path, title: str | None = None) -> Path:
    files = iter_episode_files(source)
    if not files:
        raise SystemExit(f"未找到可导出的分集源稿：{source}")
    doc = _setup_document()
    if title:
        add_title(doc, title)
    for i, f in enumerate(files):
        if i > 0:
            add_body_paragraph(doc, "")
        for line in iter_source_lines(f.read_text(encoding="utf-8")):
            add_body_paragraph(doc, line)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    return output


def main() -> None:
    p = argparse.ArgumentParser(description="将分集源稿导出为宁式 Word")
    p.add_argument("path", help="项目目录或单个分集文件")
    p.add_argument("-o", "--output", required=True, help="输出的 .docx 路径")
    p.add_argument("--title", default=None, help="可选剧名，写入文头居中标题；未给则只导出分集正文")
    args = p.parse_args()
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"路径不存在：{path}")
    out = Path(args.output)
    if out.suffix.lower() != ".docx":
        out = out.with_suffix(".docx")
    written = export_docx(path, out, title=args.title)
    print(f"已导出：{written}")


if __name__ == "__main__":
    main()
