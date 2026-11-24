#!/usr/bin/env python3
"""分集源稿的共用处理：规范化 Markdown、扫描分集、按两种口径计字。

源稿可用 Markdown 标题和加粗；本模块先剥掉行首 `#` 和包裹的 `**`，保留文字，
再分别计字或导出。例如：

- `### 1-1 客厅 夜 内` → `1-1 客厅 夜 内`（场头仍在）
- `## 第1集` → `第1集`
- `**艾拉**（冷笑）：` → `艾拉（冷笑）：`

两种字数口径（都在剥掉 Markdown 符号之后计算）：

- 本包口径：跳过集标题、场头、人物行和整行制作标记；中文标点与 △ 不计；
  制作类【标记】整段去掉；内容类【标记】只计括号里的文字。
- Word 近似口径：集标题、场头、人物行、中文标点、△ 都算进去。
  这是尽量接近 Word「字数」的近似，不是打开 Word 后的官方统计。
"""
from __future__ import annotations

import re
from pathlib import Path

EPISODE_MD_NAME = re.compile(r"^第\d+集\.md$")
EPISODE_TXT_NAME = re.compile(r"^ep.+\.txt$", re.IGNORECASE)

_CN_NUM = r"[一二三四五六七八九十百千零〇两]+"
_AR_NUM = r"[0-9０-９]+"

# 规范化之后再匹配：第1集 / 第 1 集 / 第一集 / 第1集 背叛 / 第1集：背叛 / 第1集《背叛》
EPISODE_TITLE = re.compile(
    rf"^第[ \t\u3000]*(?:{_AR_NUM}|{_CN_NUM})[ \t\u3000]*集"
    r"(?:$|[ \t\u3000：:（(《].*)"
)

# 1-1 客厅 / 1-1客厅 / 1-1　客厅 / 1-1-1 回忆 / 1-1 具体地点  夜  内
SCENE_HEADER = re.compile(
    r"^\d{1,3}-\d{1,3}(?:-\d{1,3})?(?:$|[ \t\u3000]|[\u4e00-\u9fff])"
)

CHAR_LINE = re.compile(r"^人物\s*[:：]")

# 制作类标记整段去掉，不计字。允许【闪回—三年前】【音效：敲门】这类带说明的写法。
_PROD_KIND = r"(?:闪回结束|回到现在|切回现在|特写|闪回|回忆|梦境|音效|画面|VO|OS)"
PROD_TAG = re.compile(rf"【{_PROD_KIND}(?:[：:\-—－].*?)?】")
PURE_PROD_MARKER = re.compile(rf"^△?\s*【{_PROD_KIND}(?:[：:\-—－].*?)?】\s*$")

# 内容类标记只计冒号/破折号后面的文字：字幕、弹幕、短信、新闻。
_CONTENT_KIND = r"(?:电视新闻|手机短信|新闻|字幕|弹幕\d*|短信)"
CONTENT_TAG = re.compile(rf"【({_CONTENT_KIND})(?:[：:\-—－](.*?))?】")

# $5,000,000 / 1,200 / 3.14 / 30% / ¥100 / 2024
NUMBER_TOKEN = re.compile(
    r"(?:[$¥€£]\s*)?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*[%％])?"
)

# Word 近似口径要计入的标点和 △（不含空白）。
WORD_PUNCT = re.compile(
    r"[△，。！？、；：""''“”‘’（）()【】《》〈〉…—–·"
    r"\u3001-\u303F"
    r"\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF65"
    r"!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]"
)

HR_LINE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")

# --front 未指定文件时，按此顺序纳入项目里已经存在的约定文头。
CONVENTIONAL_FRONT = (
    "benchmark.md",
    "对标.md",
    "对标笔记.md",
    "creative-plan.md",
    "characters.md",
)

# 对白：优先认「姓名（情绪）：」；无情绪括号时，只在句号等收束后拆开，
# 避免把「△现在时间：深夜。」误判成对白。
_NAME = r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z·.\-]{0,11}"
DIALOGUE_EMOTION = re.compile(rf"({_NAME}（[^）]+）[：:])")
DIALOGUE_AFTER_STOP = re.compile(rf"(?<=[。！？…!?])({_NAME}[：:])")
DIALOGUE_AT = re.compile(rf"(?:^|(?<=\s)|(?<=△)|(?<=[。！？…!?]))({_NAME}(?:（[^）]+）)?[：:])")


class EpisodeScanError(Exception):
    """分集扫描或集号校验失败。"""


def normalize_source_line(line: str) -> str:
    """去掉行首标题 `#` 和包裹的 `**`，保留文字。"""
    s = line.rstrip("\n\r")
    m = re.match(r"^(#{1,6})([ \t\u3000]*)(.*)$", s)
    if m:
        rest = m.group(3)
        rest = re.sub(r"[ \t\u3000]+#+\s*$", "", rest)
        s = rest
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return s


def skip_frontmatter_and_shell(text: str) -> list[str]:
    """去掉 YAML frontmatter、引用行和分隔线，返回待处理的正文行（尚未规范化）。"""
    lines = text.splitlines()
    out: list[str] = []
    in_frontmatter = False
    for i, raw in enumerate(lines):
        s = raw.rstrip("\n\r")
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
        if HR_LINE.match(stripped):
            continue
        out.append(s)
    return out


def normalized_body_lines(text: str) -> list[str]:
    """正文行，已剥掉 Markdown 符号。"""
    return [normalize_source_line(s) for s in skip_frontmatter_and_shell(text)]


def is_skippable_line(line: str) -> bool:
    """本包口径下整行不计字。传入行可以带 Markdown 符号。"""
    s = normalize_source_line(line).strip()
    if not s:
        return True
    if EPISODE_TITLE.match(s):
        return True
    if SCENE_HEADER.match(s):
        return True
    if CHAR_LINE.match(s):
        return True
    if PURE_PROD_MARKER.match(s):
        return True
    return False


def visible_text(line: str) -> str:
    """本包口径：去掉制作类标记，内容类标记只留括号里的文字。"""
    text = PROD_TAG.sub("", line)
    text = CONTENT_TAG.sub(lambda m: m.group(2) or "", text)
    return text


def _count_pack_tokens(text: str) -> int:
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    without_numbers, n_count = NUMBER_TOKEN.subn(" ", text)
    latin = len(re.findall(r"[A-Za-z]+", without_numbers))
    return han + latin + n_count


def _count_word_tokens(text: str) -> int:
    """汉字 + 标点（含 △）+ 英文单词 + 金额/数字。空白不计。"""
    without_numbers, n_count = NUMBER_TOKEN.subn(" ", text)
    han = len(re.findall(r"[\u4e00-\u9fff]", without_numbers))
    punct = len(WORD_PUNCT.findall(without_numbers))
    latin = len(re.findall(r"[A-Za-z]+", without_numbers))
    return han + punct + latin + n_count


def count_text(text: str) -> int:
    """本包口径。"""
    n = 0
    for line in normalized_body_lines(text):
        if is_skippable_line(line):
            continue
        n += _count_pack_tokens(visible_text(line))
    return n


def count_text_word_approx(text: str) -> int:
    """Word 近似口径：场头、人物行、集标题、中文标点、△ 都计入。

    这是近似，不是 Microsoft Word 打开文件后的官方统计。
    """
    n = 0
    for line in normalized_body_lines(text):
        if not line.strip():
            continue
        n += _count_word_tokens(line)
    return n


def episode_number(path: Path) -> int | None:
    m = re.search(r"第(\d+)集", path.name)
    if m:
        return int(m.group(1))
    m = re.search(r"ep(\d+)", path.name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def iter_episode_files(path: Path) -> list[Path]:
    """收集待统计或导出的分集文件。

    有 `episodes/` 时只读该目录、不递归；没有它才回退到项目根目录的
    `第N集.md` 或 `ep*.txt`。回退也不扫描任意子目录里的草稿。
    """
    path = Path(path)
    if path.is_file():
        return [path]

    episodes_dir = path / "episodes"
    if episodes_dir.is_dir():
        candidates = [f for f in episodes_dir.iterdir() if f.is_file()]
    else:
        candidates = list(path.glob("第*集.md")) + list(path.glob("ep*.txt"))

    uniq: list[Path] = []
    seen: set[Path] = set()
    for f in candidates:
        if not f.is_file():
            continue
        name = f.name
        if EPISODE_MD_NAME.match(name) or EPISODE_TXT_NAME.match(name):
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                uniq.append(f)

    def sort_key(p: Path) -> tuple[int, int, str]:
        n = episode_number(p)
        if n is not None and "第" in p.name:
            return (0, n, p.as_posix())
        if n is not None:
            return (1, n, p.as_posix())
        return (2, 0, p.as_posix())

    uniq.sort(key=sort_key)
    return uniq


def validate_episode_files(files: list[Path], expected: int | None = None) -> None:
    """同一集号出现两次一律报错；传入预期集数时，缺集或多集也报错。"""
    nums: dict[int, Path] = {}
    for f in files:
        n = episode_number(f)
        if n is None:
            raise EpisodeScanError(f"无法识别集号：{f}")
        if n in nums:
            raise EpisodeScanError(
                f"同一集号出现两次：第{n}集（{nums[n]} 与 {f}）"
            )
        nums[n] = f
    if expected is None:
        return
    missing = [i for i in range(1, expected + 1) if i not in nums]
    extra = sorted(n for n in nums if n < 1 or n > expected)
    parts: list[str] = []
    if missing:
        parts.append("缺集：" + "、".join(f"第{i:02d}集" for i in missing))
    if extra:
        parts.append(
            f"传了 --episodes {expected}，但出现了"
            + "、".join(f"第{n:02d}集" for n in extra)
        )
    if parts:
        raise EpisodeScanError("；".join(parts))


def resolve_front_files(project: Path, front: list[str] | None) -> list[Path]:
    """解析 --front：None 表示不导文头；空列表表示用约定文件；否则用给定路径。"""
    if front is None:
        return []
    if not front:
        return [project / name for name in CONVENTIONAL_FRONT if (project / name).is_file()]
    out: list[Path] = []
    for item in front:
        for part in item.split(","):
            part = part.strip()
            if not part:
                continue
            p = Path(part)
            if not p.is_absolute():
                p = project / p
            if not p.is_file():
                raise EpisodeScanError(f"文头文件不存在：{p}")
            out.append(p)
    return out


def tidy_ning_lines(lines: list[str]) -> list[str]:
    """导出前的最小整理：孤独的 △ 并入下一动作行；△ 与对白同行则拆开。"""
    split: list[str] = []
    for raw in lines:
        if not raw.strip():
            split.append("")
            continue
        s = raw.strip()
        if "△" in s:
            m = DIALOGUE_EMOTION.search(s)
            if m is None:
                m = DIALOGUE_AFTER_STOP.search(s)
            if m and m.start() > 0:
                before = s[: m.start()].strip()
                after = s[m.start() :].strip()
                if before and before != "△":
                    split.append(before)
                split.append(after)
                continue
        split.append(s)

    out: list[str] = []
    i = 0
    while i < len(split):
        s = split[i]
        if s.strip() == "△":
            j = i + 1
            while j < len(split) and not split[j].strip():
                j += 1
            if j < len(split):
                nxt = split[j].strip()
                if nxt.startswith("△"):
                    out.append(nxt)
                elif DIALOGUE_AT.match(nxt):
                    # 对白前的孤独 △ 丢弃，对白单独成行
                    out.append(nxt)
                else:
                    out.append("△" + nxt)
                i = j + 1
                continue
        out.append(s)
        i += 1
    return out


def collapse_blank_lines(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    collapsed: list[str] = []
    blank = False
    for line in trimmed:
        if not line.strip():
            if not blank:
                collapsed.append("")
            blank = True
        else:
            collapsed.append(line.strip())
            blank = False
    return collapsed
