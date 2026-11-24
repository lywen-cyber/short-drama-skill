#!/usr/bin/env python3
"""把项目 Markdown 源稿导出为宁式排版的 Word。

宁式（与 references/正文格式.md 一致，未另给格式时的默认）：
- 动作和画面用 △，与后面的文字同一段，不单独一行只放一个三角；
- 对白另起一行，一般不与 △ 混在同一段；
- 场头、人物行、△ 段落、对白都按源稿分段写出，不临场改写正文。

源稿可用 Markdown 标题和加粗。导出前会剥掉行首 `#` 和包裹的 `**`，保留文字：
`### 1-1 客厅 夜 内` 在 Word 里仍是场头；`**艾拉**（冷笑）：` 只去掉加粗标记。
导出时还会做最小整理：一行只剩 △ 则并入下一动作行；△ 与对白写在同一行则拆开。

排版固定为：A4；左右页边距 1.25 英寸、上下 1 英寸；
正文 10.5 磅宋体（西文 Times New Roman）、两端对齐；
可选剧名用 16 磅黑体（西文 Arial）、加粗、居中。

有 `episodes/` 时只读该目录、不递归；没有它才回退到根目录的 `第N集.md` 或 `ep*.txt`。
同一集号出现两次，或传了 --episodes N 却缺集、多集，都会报错退出。

用法：
  python scripts/export_docx.py <项目目录或分集文件> -o 剧名.docx
  python scripts/export_docx.py examples/示例项目 --title 示例项目 -o /tmp/示例项目.docx
  python scripts/export_docx.py examples/示例项目 --front --title 示例项目 -o /tmp/示例项目.docx

`--front` 在分集正文前写入文头：只写该参数时，按约定顺序纳入项目里已有的
对标笔记、大纲（creative-plan.md）、人物小传（characters.md）；也可再跟文件路径。
不要把过程稿或非本项目材料塞进文头。

交稿前的字数请用 scripts/count.py 同时看两种口径，本脚本不负责字数。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt

from script_text import (
    EpisodeScanError,
    collapse_blank_lines,
    iter_episode_files,
    normalized_body_lines,
    resolve_front_files,
    tidy_ning_lines,
    validate_episode_files,
)

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
    """从源稿取出要写入 Word 的行：剥掉 Markdown 符号，保留场头和正文。"""
    lines = collapse_blank_lines(normalized_body_lines(text))
    return tidy_ning_lines(lines)


def add_body_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run(text if text else "")
    _set_run_font(run, east=EAST_BODY, ascii_font=ASCII_BODY, size_pt=10.5)


def add_title(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(13)
    run = p.add_run(title)
    _set_run_font(run, east=EAST_TITLE, ascii_font=ASCII_TITLE, size_pt=16, bold=True)


def export_docx(
    source: Path,
    output: Path,
    title: str | None = None,
    *,
    front: list[str] | None = None,
    episodes: int | None = None,
) -> Path:
    source = Path(source)
    files = iter_episode_files(source)
    if not files:
        raise SystemExit(f"未找到可导出的分集源稿：{source}")
    project = source if source.is_dir() else source.parent
    if source.is_dir():
        try:
            validate_episode_files(files, episodes)
            front_files = resolve_front_files(project, front)
        except EpisodeScanError as e:
            raise SystemExit(str(e)) from e
    else:
        try:
            front_files = resolve_front_files(project, front)
        except EpisodeScanError as e:
            raise SystemExit(str(e)) from e

    doc = _setup_document()
    if title:
        add_title(doc, title)
    for i, f in enumerate(front_files):
        if i > 0:
            add_body_paragraph(doc, "")
        for line in iter_source_lines(f.read_text(encoding="utf-8")):
            add_body_paragraph(doc, line)
    if front_files:
        add_body_paragraph(doc, "")
    for i, f in enumerate(files):
        if i > 0:
            add_body_paragraph(doc, "")
        for line in iter_source_lines(f.read_text(encoding="utf-8")):
            add_body_paragraph(doc, line)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    return output


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="将分集源稿导出为宁式 Word")
    p.add_argument("path", help="项目目录或单个分集文件")
    p.add_argument("-o", "--output", required=True, help="输出的 .docx 路径")
    p.add_argument("--title", default=None, help="可选剧名，写入文头居中标题；未给则只导出分集正文")
    p.add_argument(
        "--front",
        nargs="*",
        default=None,
        metavar="FILE",
        help="在分集前写入文头。只写 --front 时按约定纳入已有的对标、大纲、人物小传；也可再跟文件路径",
    )
    p.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="预期集数；缺集或多集则报错退出，避免把范围外的稿导进去",
    )
    args = p.parse_args(argv)
    path = Path(args.path)
    if not path.exists():
        print(f"路径不存在：{path}", file=sys.stderr)
        return 1
    out = Path(args.output)
    if out.suffix.lower() != ".docx":
        out = out.with_suffix(".docx")
    try:
        written = export_docx(path, out, title=args.title, front=args.front, episodes=args.episodes)
    except SystemExit as e:
        if e.code not in (None, 0):
            msg = e.code if isinstance(e.code, str) else str(e)
            if msg and msg not in ("1", "0"):
                print(msg, file=sys.stderr)
            return 1
        raise
    print(f"已导出：{written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
