#!/usr/bin/env python3
"""轻量分集检查：场头、本场人物、小传人名、△ 排法。

供 /review 先跑。只查机器能稳定判断的格式和一致性问题，不做剧情评判。
「冷笑」「一脸」这类神态词，以及「你也知道」这类陈词滥调，只统计报告，不当错误。
发现问题以非零退出。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from script_text import (  # noqa: E402
    CHAR_LINE,
    DIALOGUE_AT,
    EPISODE_TITLE,
    EpisodeScanError,
    SCENE_HEADER,
    HR_LINE,
    iter_episode_files,
    normalize_source_line,
)

# 几乎是场头、但分隔符不是「N-N」：1.1 客厅、第一场、场头：……
ALMOST_SCENE = re.compile(
    r"^(?:"
    r"\d{1,3}\s*[.．—－_~～/／]\s*\d{1,3}"
    r"|场[次头]?\s*[:：]"
    r"|第[0-9０-９一二三四五六七八九十百]+场"
    r")"
)
# 短行以「日/夜 + 内/外」收束，常见漏写集号的场头。
SCENE_TAIL = re.compile(r"[日夜][ \t\u3000]*[内外]\s*$")

PRONOUN_SPEAKERS = {"她", "他", "它", "我", "你", "我们", "你们", "他们", "她们", "咱", "咱们"}
NOT_SPEAKERS = {
    "现在时间",
    "时间",
    "地点",
    "画面",
    "镜头",
    "字幕",
    "旁白",
    "备注",
    "说明",
    "注释",
    "同时",
    "此时",
    "突然",
    "随后",
    "接着",
    "然后",
    "于是",
    "原来",
    "其实",
    "但是",
    "可是",
    "只是",
    "还有",
    "以及",
    "因为",
    "所以",
    "如果",
    "为了",
    "关于",
    "至于",
    "画外音",
    "画外",
    "内",
    "外",
    "日",
    "夜",
    "VO",
    "OS",
    "vo",
    "os",
}

MANNERISMS = (
    "冷笑",
    "一脸",
    "嘴角",
    "愣住",
    "深吸一口气",
    "微微一笑",
    "眼神一凛",
    "咬牙",
    "眼眶",
)

# 只统计报告，不当硬错误。清单与 references/对白.md 保持一致。
CLICHES = (
    "我很生气",
    "我很伤心",
    "我很害怕",
    "我很高兴",
    "你也知道",
    "众所周知",
    "事情是这样的",
    "说来话长",
    "你听我解释",
    "你给我听好了",
    "你给我记住",
    "你会后悔的",
    "走着瞧",
    "从今以后",
    "放尊重一点",
    "你算什么东西",
    "你配吗",
    "贱人",
    "这不可能",
    "绝不会放过你",
)

_HEADING_NAME = re.compile(r"^#{2,6}[ \t\u3000]+(.+?)\s*$")
_SHORT_NAME = re.compile(
    r"(?:正文短名|短名|译名)\s*[:：]\s*([^\s；;，,。.【\[]+)"
)


@dataclass(frozen=True)
class Issue:
    path: Path
    line: int
    message: str

    def format(self) -> str:
        rel = self.path
        return f"{rel}:{self.line}  {self.message}"


def iter_numbered_body_lines(text: str) -> list[tuple[int, str]]:
    """返回 (1-based 行号, 规范化后的正文行)，跳过 frontmatter、引用和分隔线。"""
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    in_frontmatter = False
    for i, raw in enumerate(lines, start=1):
        s = raw.rstrip("\n\r")
        if i == 1 and s.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if s.strip() == "---":
                in_frontmatter = False
            continue
        stripped = s.strip()
        if stripped.startswith(">"):
            continue
        if HR_LINE.match(stripped):
            continue
        out.append((i, normalize_source_line(s)))
    return out


def is_lone_triangle(norm: str) -> bool:
    s = norm.strip()
    return bool(s) and re.fullmatch(r"△+", s) is not None


def classify_scene_line(norm: str) -> str:
    """valid / invalid / other。"""
    s = norm.strip()
    if not s:
        return "other"
    if SCENE_HEADER.match(s):
        return "valid"
    if ALMOST_SCENE.match(s):
        return "invalid"
    if s.startswith("△"):
        return "other"
    if speakers_in_line(s):
        return "other"
    if SCENE_TAIL.search(s) and len(s) <= 40:
        return "invalid"
    return "other"


def speakers_in_line(norm: str) -> list[str]:
    names: list[str] = []
    for m in DIALOGUE_AT.finditer(norm):
        raw = m.group(1)
        name = re.sub(r"（[^）]+）\s*[：:]$", "", raw)
        name = re.sub(r"[：:]$", "", name).strip()
        if not name:
            continue
        if name in NOT_SPEAKERS or name.upper() in {"VO", "OS"}:
            continue
        names.append(name)
    return names


def parse_scene_cast(norm: str) -> list[str]:
    s = CHAR_LINE.sub("", norm).strip()
    s = s.replace("【", "").replace("】", "").strip()
    if not s:
        return []
    parts = [p.strip() for p in re.split(r"[、，,;；/／]+", s) if p.strip()]
    out: list[str] = []
    for p in parts:
        out.append(p)
        tokens = p.split()
        if len(tokens) >= 2 and tokens[0][0].isascii() and tokens[0][0].isalpha():
            out.append(tokens[0])
    return out


def _add_roster_name(raw: str, names: set[str]) -> None:
    s = raw.strip()
    s = re.sub(r"[（(][^）)]*[）)]", "", s).strip()
    s = s.strip("：:：-—– ")
    if not s or s.startswith("【") or s.startswith("["):
        return
    if "小传" in s or s.endswith("人物") or s.startswith("示例"):
        return
    for part in re.split(r"[/／、，,]+", s):
        part = part.strip()
        if not part or part.startswith("【"):
            continue
        names.add(part)
        tokens = part.split()
        if len(tokens) >= 2 and tokens[0][0].isascii() and tokens[0][0].isalpha():
            names.add(tokens[0])


def parse_character_roster(text: str) -> set[str]:
    """从 characters.md 提取人名：二级及以下标题，以及短名 / 译名。"""
    names: set[str] = set()
    for raw in text.splitlines():
        hm = _HEADING_NAME.match(raw.rstrip("\n\r"))
        if hm:
            _add_roster_name(hm.group(1), names)
            continue
        s = normalize_source_line(raw).strip()
        for m in _SHORT_NAME.finditer(s):
            _add_roster_name(m.group(1), names)
    return names


def find_characters_file(path: Path) -> Path | None:
    path = Path(path)
    if path.is_file():
        roots = [path.parent]
        if path.parent.name == "episodes":
            roots.append(path.parent.parent)
    else:
        roots = [path]
    for root in roots:
        cand = root / "characters.md"
        if cand.is_file():
            return cand
    return None


def name_in(name: str, roster: list[str] | set[str]) -> bool:
    roster_list = list(roster)
    if name in roster_list:
        return True
    lowered = {r.lower() for r in roster_list}
    if name.lower() in lowered:
        return True
    return False


def lint_episode(path: Path, roster: set[str] | None) -> tuple[list[Issue], Counter[str]]:
    text = path.read_text(encoding="utf-8")
    issues: list[Issue] = []
    manner: Counter[str] = Counter()
    current_scene: str | None = None
    current_cast: list[str] | None = None  # None = 尚无人物行

    for lineno, norm in iter_numbered_body_lines(text):
        s = norm.strip()
        if not s:
            continue
        if EPISODE_TITLE.match(s):
            continue

        kind = classify_scene_line(s)
        if kind == "valid":
            current_scene = s
            current_cast = None
            continue
        if kind == "invalid":
            issues.append(Issue(path, lineno, f"场头无法识别：{s}"))
            current_scene = s
            current_cast = None
            continue

        if CHAR_LINE.match(s):
            if current_scene is None:
                issues.append(Issue(path, lineno, "人物行出现在可识别场头之前"))
            current_cast = parse_scene_cast(s)
            if not current_cast:
                issues.append(Issue(path, lineno, "人物行没有可识别的人名"))
            continue

        if is_lone_triangle(s):
            issues.append(Issue(path, lineno, "△ 单独成行，应与后面的动作写在同一段"))

        speakers = speakers_in_line(s)
        # 只在 △ 出现在说话人之前时判定为挤在同一段，避免对白里提到「△」误报。
        if speakers:
            first = DIALOGUE_AT.search(s)
            tri = s.find("△")
            if first is not None and tri != -1 and tri < first.start():
                issues.append(Issue(path, lineno, "△ 与对白挤在同一段，对白应另起一行"))

        if speakers:
            if current_scene is None:
                issues.append(Issue(path, lineno, "对白出现在可识别场头之前"))
            elif current_cast is None:
                issues.append(Issue(path, lineno, "本场没有人物行，无法核对说话人"))
            for name in speakers:
                if name in PRONOUN_SPEAKERS:
                    issues.append(
                        Issue(path, lineno, f"说话人写成「{name}」，应改成姓名")
                    )
                    continue
                if current_cast is not None and not name_in(name, current_cast):
                    issues.append(
                        Issue(
                            path,
                            lineno,
                            f"说话人「{name}」未出现在本场人物表",
                        )
                    )
                if roster is not None and not name_in(name, roster):
                    issues.append(
                        Issue(
                            path,
                            lineno,
                            f"说话人「{name}」未出现在人物小传中",
                        )
                    )

        if not is_lone_triangle(s) and not CHAR_LINE.match(s):
            for word in MANNERISMS:
                c = s.count(word)
                if c:
                    manner[word] += c
            for word in CLICHES:
                c = s.count(word)
                if c:
                    manner[word] += c

    return issues, manner


def lint_path(path: Path) -> tuple[list[Issue], Counter[str], Path | None]:
    """检查项目目录或单个分集。返回 (问题, 神态词统计, characters.md 路径或 None)。"""
    path = Path(path)
    files = iter_episode_files(path)
    if not files:
        raise EpisodeScanError(f"未找到分集文件：{path}")
    chars = find_characters_file(path)
    roster: set[str] | None = None
    if chars is not None:
        roster = parse_character_roster(chars.read_text(encoding="utf-8"))
        if not roster:
            roster = None
    issues: list[Issue] = []
    manner: Counter[str] = Counter()
    for f in files:
        ep_issues, ep_manner = lint_episode(f, roster)
        issues.extend(ep_issues)
        manner.update(ep_manner)
    return issues, manner, chars


def format_mannerisms(manner: Counter[str]) -> str | None:
    """格式化神态词与陈词滥调报告；没有命中时返回 None。"""
    blocks: list[str] = []
    manner_parts = [f"{w} {manner[w]}" for w in MANNERISMS if manner[w]]
    if manner_parts:
        blocks.append("神态词统计（只报告，不当错误）：" + "，".join(manner_parts))
    cliche_parts = [f"{w} {manner[w]}" for w in CLICHES if manner[w]]
    if cliche_parts:
        blocks.append("陈词滥调统计（只报告，不当错误）：" + "，".join(cliche_parts))
    return "\n".join(blocks) if blocks else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="轻量检查分集场头、说话人和 △ 排法；神态词和陈词滥调只报告。"
    )
    p.add_argument("path", help="项目目录或单个分集文件")
    args = p.parse_args(argv)
    path = Path(args.path)
    if not path.exists():
        print(f"路径不存在：{path}", file=sys.stderr)
        return 1
    try:
        issues, manner, _chars = lint_path(path)
    except EpisodeScanError as e:
        print(str(e), file=sys.stderr)
        return 1

    for issue in issues:
        print(issue.format())
    report = format_mannerisms(manner)
    if report:
        if issues:
            print()
        print(report)
    if issues:
        print(f"\n发现 {len(issues)} 个问题。")
        return 1
    if not report:
        print("未发现问题。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
