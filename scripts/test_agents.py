#!/usr/bin/env python3
"""审稿编辑 agent 文件的回归测试：两份内容一致、frontmatter 合规、关键规则在。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAIN = REPO / "agents" / "审稿编辑.md"
CLAUDE = REPO / ".claude" / "agents" / "审稿编辑.md"


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class AgentFilesTest(unittest.TestCase):
    def test_both_files_identical(self) -> None:
        self.assertEqual(MAIN.read_text(encoding="utf-8"), CLAUDE.read_text(encoding="utf-8"))

    def test_frontmatter(self) -> None:
        fm = frontmatter(MAIN.read_text(encoding="utf-8"))
        self.assertRegex(fm.get("name", ""), r"^[a-z][a-z0-9-]*$")
        self.assertTrue(fm.get("description"))

    def test_key_rules_present(self) -> None:
        text = MAIN.read_text(encoding="utf-8")
        for needle in (
            "brief.md",
            "episode-directory.md",
            "continuity.md",
            "没有引文的分数作废",
            "最多两轮",
            "交人工",
            "写手不能改分",
            "梗概模式",
            "买不买",
            "卖点",
            "严重度固定为「建议」",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
