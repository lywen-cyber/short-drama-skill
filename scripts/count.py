#!/usr/bin/env python3
"""按当次 brief 统计正文词字数（汉字个数 + 英文单词数，不计空白）。

默认跳过、不计入字数：
- 集标题行：如「第1集」「第 1 集」「第一集」「第01集」「第1集 背叛」
  以及对应的 Markdown 标题行；
- 场头：如「1-1 客厅」「1-1客厅」（含全角空格）、「1-1-1 回忆」这类闪回场号；
- 以「人物：」或「人物:」开头的行。

【音效】【闪回】【回忆】这类标记：
- 整行只是幕头或音效标记的，不计正文字；
- 嵌在动作段落中的，去掉标记本身，只统计对外可见的描述。

数字与金额：带货币符号、千分位或百分号的数字（如 $5,000,000、1,200、30%）
按 1 个英文单词计，避免商战戏里的金额被记成 0 字。普通连续数字同样按 1 词计。

交稿前的字数以 Markdown 源稿为准，本脚本不直接读 .docx。

按目录统计时，默认扫描 `episodes/第NN集.md`（两位编号），
同时兼容旧的 `ep*.txt` 和项目根目录的 `第N集.md`。
上下限和集数来自参数；不传则只打印数字，不判定合格。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

EPISODE_MD_NAME = re.compile(r"^第\d+集\.md$")
EPISODE_TXT_NAME = re.compile(r"^ep.+\.txt$", re.IGNORECASE)

# 第1集 / 第 1 集 / 第01集 / 第一集 / 第1集 背叛 / # 第 1 集……
_CN_NUM = r"[一二三四五六七八九十百千零〇两]+"
_AR_NUM = r"[0-9０-９]+"
EPISODE_TITLE = re.compile(
    rf"^#{{0,6}}\s*第[ \t\u3000]*(?:{_AR_NUM}|{_CN_NUM})[ \t\u3000]*集"
    r"(?:$|[ \t\u3000].*|（.*|\(.*)"
)

# 1-1 客厅 / 1-1客厅 / 1-1　客厅 / 1-1-1 回忆 / 1-1 具体地点  夜  内
SCENE_HEADER = re.compile(
    r"^\d{1,3}-\d{1,3}(?:-\d{1,3})?(?:$|[ \t\u3000]|[\u4e00-\u9fff])"
)

CHAR_LINE = re.compile(r"^人物\s*[:：]")

# 整行只是 △＋【标记】
PURE_MARKER = re.compile(r"^△?\s*【[^】]+】\s*$")

# 嵌在段落中的制作标记，不计字，只留可见描述
PROD_TAG = re.compile(
    r"【(?:音效|闪回|闪回结束|回忆|回到现在|切回现在|梦境|字幕|特写|画面|VO|OS)】"
)

# $5,000,000 / 1,200 / 3.14 / 30% / ¥100 / 2024
NUMBER_TOKEN = re.compile(
    r"(?:[$¥€£]\s*)?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*[%％])?"
)

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", ".idea", ".vscode"}


def is_skippable_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if EPISODE_TITLE.match(s):
        return True
    if SCENE_HEADER.match(s):
        return True
    if CHAR_LINE.match(s):
        return True
    if PURE_MARKER.match(s):
        return True
    return False


def visible_text(line: str) -> str:
    """去掉制作标记，留下对外可见描述。"""
    return PROD_TAG.sub("", line)


def count_visible(text: str) -> int:
    text = visible_text(text)
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    without_numbers, n_count = NUMBER_TOKEN.subn(" ", text)
    latin = len(re.findall(r"[A-Za-z]+", without_numbers))
    return han + latin + n_count


def count_text(text: str) -> int:
    n = 0
    for line in text.splitlines():
        if is_skippable_line(line):
            continue
        n += count_visible(line)
    return n


def _is_under_skipped_dir(path: Path, root: Path) -> bool:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        parts = path.parts
    return any(part in SKIP_DIRS for part in parts)


def iter_episode_files(path: Path) -> list[Path]:
    """收集待统计的分集文件。path 可以是文件或目录。"""
    path = Path(path)
    if path.is_file():
        return [path]

    candidates: list[Path] = []
    # 现行约定：episodes/第NN集.md
    candidates += path.glob("episodes/第*集.md")
    candidates += path.glob("**/episodes/第*集.md")
    # 兼容旧项目：根目录或任意子目录的 第N集.md
    candidates += path.glob("第*集.md")
    candidates += path.glob("**/第*集.md")
    # 兼容更旧的 ep*.txt
    candidates += path.glob("ep*.txt")
    candidates += path.glob("**/ep*.txt")

    seen: set[Path] = set()
    uniq: list[Path] = []
    root = path if path.is_dir() else path.parent
    for f in candidates:
        if not f.is_file():
            continue
        if _is_under_skipped_dir(f, root):
            continue
        name = f.name
        if EPISODE_MD_NAME.match(name) or EPISODE_TXT_NAME.match(name):
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                uniq.append(f)

    def sort_key(p: Path) -> tuple[int, int, str]:
        m = re.search(r"第(\d+)集", p.name)
        if m:
            return (0, int(m.group(1)), p.as_posix())
        m = re.search(r"ep(\d+)", p.name, re.IGNORECASE)
        if m:
            return (1, int(m.group(1)), p.as_posix())
        return (2, 0, p.as_posix())

    uniq.sort(key=sort_key)
    return uniq


def main() -> None:
    p = argparse.ArgumentParser(description="统计分集正文词字数")
    p.add_argument("path", nargs="?", default=".", help="目录或单个文件")
    p.add_argument("--min", type=int, default=None, help="当次每集下限")
    p.add_argument("--max", type=int, default=None, help="当次每集上限")
    p.add_argument("--episodes", type=int, default=None, help="预期集数（只用于目录扫描提示）")
    args = p.parse_args()
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"路径不存在：{path}")
    files = iter_episode_files(path)
    if not files:
        raise SystemExit(f"未找到可统计文件：{path}")
    total = 0
    for f in files:
        n = count_text(f.read_text(encoding="utf-8"))
        total += n
        flag = ""
        if args.min is not None and n < args.min:
            flag = " 低于下限"
        elif args.max is not None and n > args.max:
            flag = " 超过上限"
        elif args.min is not None or args.max is not None:
            flag = " 合格"
        try:
            label = f.resolve().relative_to(path.resolve()) if path.is_dir() else f.name
        except ValueError:
            label = f.name
        print(f"{label}: {n}{flag}")
    print(f"合计: {total}")
    if args.episodes is not None and path.is_dir():
        print(f"已统计 {len(files)} 个文件，brief 集数为 {args.episodes}")


if __name__ == "__main__":
    main()
