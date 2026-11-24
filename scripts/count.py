#!/usr/bin/env python3
"""按当次 brief 统计正文词字数，同时输出本包口径和 Word 近似口径。

本包口径（默认，用来判定 --min/--max，可用 --metric 改成 Word 近似）：
- 跳过集标题行：如「第1集」「第 1 集」「第一集」「第01集」「第1集 背叛」
  「第1集：背叛」「第1集《背叛》」，以及对应的 Markdown 标题行；
- 跳过场头：如「1-1 客厅」「1-1客厅」（含全角空格）、「1-1-1 回忆」，
  以及写成 `### 1-1 客厅 夜 内` 的标题行（会先剥掉 `#` 再判断）；
- 跳过以「人物：」或「人物:」开头的行。
- 制作类标记（音效、特写、闪回等）：整行不计；嵌在段落中的整段去掉，
  包括【闪回—三年前】这类带说明的写法，不把说明文字算进正文。
- 内容类标记（字幕、弹幕、短信、新闻）：只计括号里的文字。整行内容类
  标记不再记 0。
- 中文标点与 △ 不计。
- 数字与金额：带货币符号、千分位或百分号的数字（如 $5,000,000、1,200、30%）
  按 1 个英文单词计。普通连续数字同样按 1 词计。

Word 近似口径：把中文标点、△、场头、人物行、集标题也算进去。
这是尽量接近 Word「字数」的近似，不是打开 Word 后的官方统计。

源稿可用 Markdown 标题和加粗，脚本会剥掉行首 `#` 和包裹的 `**`，再计字。
交稿前两种口径都看，以 brief 指定的为准；brief 没写则默认本包口径，
并注意 Word 里看到的数字可能更大。本脚本不直接读 .docx。

按目录统计时：有 `episodes/` 就只读这个目录、不递归；没有它才回退到
项目根目录的 `第N集.md` 或 `ep*.txt`。不会扫描任意子目录里的草稿。
同一集号出现两次会报错。传了 --episodes N 却缺集或出现第 N+1 集，也会报错。
字数不合格时返回非零。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from script_text import (  # re-exported for tests and export_docx
    EpisodeScanError,
    count_text,
    count_text_word_approx,
    is_skippable_line,
    iter_episode_files,
    validate_episode_files,
    visible_text,
)

__all__ = [
    "EpisodeScanError",
    "count_text",
    "count_text_word_approx",
    "is_skippable_line",
    "iter_episode_files",
    "validate_episode_files",
    "visible_text",
]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="统计分集正文词字数（本包口径与 Word 近似口径）")
    p.add_argument("path", nargs="?", default=".", help="目录或单个文件")
    p.add_argument("--min", type=int, default=None, help="当次每集下限")
    p.add_argument("--max", type=int, default=None, help="当次每集上限")
    p.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="预期集数；目录扫描时若缺集或多集则报错退出",
    )
    p.add_argument(
        "--metric",
        choices=("pack", "word"),
        default="pack",
        help="用哪一口径判定上下限：pack=本包（默认），word=Word 近似",
    )
    args = p.parse_args(argv)
    path = Path(args.path)
    if not path.exists():
        print(f"路径不存在：{path}", file=sys.stderr)
        return 1
    files = iter_episode_files(path)
    if not files:
        print(f"未找到可统计文件：{path}", file=sys.stderr)
        return 1
    if path.is_dir():
        try:
            validate_episode_files(files, args.episodes)
        except EpisodeScanError as e:
            print(str(e), file=sys.stderr)
            return 1

    total_pack = 0
    total_word = 0
    failed = False
    for f in files:
        text = f.read_text(encoding="utf-8")
        pack = count_text(text)
        word = count_text_word_approx(text)
        total_pack += pack
        total_word += word
        judged = word if args.metric == "word" else pack
        flag = ""
        if args.min is not None and judged < args.min:
            flag = " 低于下限"
            failed = True
        elif args.max is not None and judged > args.max:
            flag = " 超过上限"
            failed = True
        elif args.min is not None or args.max is not None:
            flag = " 合格"
        try:
            label = f.resolve().relative_to(path.resolve()) if path.is_dir() else f.name
        except ValueError:
            label = f.name
        print(f"{label}: 本包 {pack} / Word近似 {word}{flag}")
    print(f"合计: 本包 {total_pack} / Word近似 {total_word}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
