#!/usr/bin/env python3
"""给分集正文标字位：每一行从本集第几字开始、占全集多少。

供 /review 与审稿编辑标出「第一次冲突」「本集转折」大概落在第几字，
抓「字数够但前一半都在铺垫」的集。只做定位，不判断哪句是冲突；
冲突和转折由审稿人判断，再用 --find 查那句原文落在哪里。

字位按本包口径（与 count.py 一致）：场头、人物行、集标题和制作类标记不计。
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from script_text import (  # noqa: E402
    EpisodeScanError,
    _count_pack_tokens,
    is_skippable_line,
    iter_episode_files,
    normalized_body_lines,
    visible_text,
)


@dataclass(frozen=True)
class LinePos:
    start: int  # 本行之前已有多少字（0 起）
    words: int  # 本行字数
    text: str


def line_positions(text: str) -> tuple[list[LinePos], int]:
    """返回 (计字行的位置列表, 全集字数)。"""
    out: list[LinePos] = []
    total = 0
    for line in normalized_body_lines(text):
        if is_skippable_line(line):
            continue
        n = _count_pack_tokens(visible_text(line))
        if n == 0:
            continue
        out.append(LinePos(total, n, line.strip()))
        total += n
    return out, total


def find_position(text: str, needle: str) -> tuple[int, int] | None:
    """needle 第一次出现的那一行的起始字位和全集字数；找不到返回 None。"""
    rows, total = line_positions(text)
    for r in rows:
        if needle in r.text:
            return r.start, total
    return None


def percent(start: int, total: int) -> int:
    return round(start * 100 / total) if total else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="标出分集正文每行的起始字位（本包口径）")
    p.add_argument("path", help="单个分集文件，或项目目录")
    p.add_argument(
        "--find",
        action="append",
        default=[],
        metavar="原文片段",
        help="只报告含该片段的第一行落在第几字；可重复",
    )
    args = p.parse_args(argv)
    path = Path(args.path)
    if not path.exists():
        print(f"路径不存在：{path}", file=sys.stderr)
        return 1
    try:
        files = [path] if path.is_file() else iter_episode_files(path)
    except EpisodeScanError as e:
        print(str(e), file=sys.stderr)
        return 1
    if not files:
        print(f"未找到分集文件：{path}", file=sys.stderr)
        return 1

    missing = False
    for f in files:
        text = f.read_text(encoding="utf-8")
        rows, total = line_positions(text)
        print(f"== {f.name}（本包 {total} 字）")
        if args.find:
            for needle in args.find:
                hit = find_position(text, needle)
                if hit is None:
                    print(f"  未找到：{needle}")
                    missing = True
                else:
                    start, _ = hit
                    print(f"  第 {start} 字（约 {percent(start, total)}%）：{needle}")
            continue
        for r in rows:
            preview = r.text if len(r.text) <= 36 else r.text[:36] + "…"
            print(f"  {r.start:>5} 字  {percent(r.start, total):>3}%  {preview}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
