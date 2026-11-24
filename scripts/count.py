#!/usr/bin/env python3
"""按当次 brief 统计正文词字数（汉字个数 + 英文单词数，不计空白）。

默认跳过整行「第N集」、以「人物：」开头的行，以及旧式场号「1-1 」。
上下限和集数来自参数；不传则只打印数字，不判定合格。
"""
import argparse
import re
from pathlib import Path


def count_text(text: str) -> int:
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^第\d+集$", s):
            continue
        if re.match(r"^\d+-\d+ ", s):
            continue
        if s.startswith("人物："):
            continue
        n += len(re.findall(r"[\u4e00-\u9fff]", s))
        n += len(re.findall(r"[A-Za-z]+", s))
    return n


def main() -> None:
    p = argparse.ArgumentParser(description="统计分集正文词字数")
    p.add_argument("path", nargs="?", default=".", help="目录或单个文件")
    p.add_argument("--min", type=int, default=None, help="当次每集下限")
    p.add_argument("--max", type=int, default=None, help="当次每集上限")
    p.add_argument("--episodes", type=int, default=None, help="预期集数（只用于目录扫描提示）")
    args = p.parse_args()
    path = Path(args.path)
    files = []
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("ep*.txt")) + sorted(path.glob("**/ep*.txt"))
        # unique
        seen = set()
        uniq = []
        for f in files:
            if f.resolve() not in seen:
                seen.add(f.resolve())
                uniq.append(f)
        files = uniq
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
        print(f"{f.name}: {n}{flag}")
    print(f"合计: {total}")
    if args.episodes is not None and path.is_dir():
        print(f"已统计 {len(files)} 个文件，brief 集数为 {args.episodes}")


if __name__ == "__main__":
    main()
