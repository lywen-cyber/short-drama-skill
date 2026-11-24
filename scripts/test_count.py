#!/usr/bin/env python3
"""count.py 口径与目录扫描的回归测试。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from count import count_text, is_skippable_line, iter_episode_files  # noqa: E402

REPO = SCRIPTS.parent
EXAMPLE = REPO / "examples" / "示例项目"


class SkipLinesTest(unittest.TestCase):
    def test_episode_titles_are_skipped(self) -> None:
        for line in (
            "第1集",
            "第 1 集",
            "第一集",
            "第01集",
            "第1集 背叛",
            "第 1 集 背叛",
            "# 第 1 集（格式占位，不是可交正文）",
        ):
            self.assertTrue(is_skippable_line(line), line)

    def test_scene_headers_are_skipped(self) -> None:
        for line in (
            "1-1 客厅",
            "1-1客厅",
            "1-1　客厅",  # 全角空格
            "1-1-1 回忆",
            "1-1 具体地点  夜  内",
        ):
            self.assertTrue(is_skippable_line(line), repr(line))

    def test_character_lines_half_and_full_colon(self) -> None:
        self.assertTrue(is_skippable_line("人物：女主、男主"))
        self.assertTrue(is_skippable_line("人物:女主、男主"))
        self.assertTrue(is_skippable_line("人物: 【本场实际出现的人】"))

    def test_pure_markers_are_skipped(self) -> None:
        for line in ("【闪回】", "【音效】", "【回忆】", "△【闪回】", "【闪回结束】"):
            self.assertTrue(is_skippable_line(line), line)

    def test_body_lines_are_not_skipped(self) -> None:
        self.assertFalse(is_skippable_line("△他推开那扇门。"))
        self.assertFalse(is_skippable_line("姓名：今天就到这里。"))
        self.assertFalse(is_skippable_line("△【音效】大门被撞开，他冲进来。"))


class CountRulesTest(unittest.TestCase):
    def test_titles_and_headers_not_counted(self) -> None:
        text = "\n".join(
            [
                "第1集 背叛",
                "第一集",
                "第 1 集",
                "1-1 客厅",
                "1-1客厅",
                "1-1-1 回忆",
                "人物: 女主",
                "人物：男主",
                "△他推开门。",
            ]
        )
        # 只计「他推开门」4 个汉字，△ 与标点不计
        self.assertEqual(count_text(text), 4)

    def test_amount_counts_as_one_word(self) -> None:
        self.assertEqual(count_text("$5,000,000"), 1)
        self.assertEqual(count_text("1,200"), 1)
        self.assertEqual(count_text("30%"), 1)
        # 汉字 + 金额 + 英文单词
        self.assertEqual(count_text("支票 $5,000,000 cash"), 2 + 1 + 1)

    def test_embedded_marker_keeps_visible_description_only(self) -> None:
        # 【音效】本身不计；「大门被撞开」5 字
        self.assertEqual(count_text("△【音效】大门被撞开"), 5)
        # 整行标记不计
        self.assertEqual(count_text("【闪回】\n△他回头。\n【闪回结束】"), 3)

    def test_latin_and_han_default(self) -> None:
        self.assertEqual(count_text("Hello 世界"), 1 + 2)


class ScanTest(unittest.TestCase):
    def test_example_project_finds_canonical_episode(self) -> None:
        files = iter_episode_files(EXAMPLE)
        names = [f.name for f in files]
        self.assertIn("第01集.md", names, names)
        self.assertTrue(any(f.parent.name == "episodes" for f in files))

    def test_legacy_layouts_still_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "第2集.md").write_text("△旧根目录。\n", encoding="utf-8")
            (root / "ep03.txt").write_text("△旧文本。\n", encoding="utf-8")
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△新路径。\n", encoding="utf-8")
            files = iter_episode_files(root)
            names = [f.name for f in files]
            self.assertEqual(names, ["第01集.md", "第2集.md", "ep03.txt"], names)
            # 按目录统计不应再报「未找到文件」
            self.assertEqual(len(files), 3)

    def test_empty_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(iter_episode_files(Path(td)), [])


if __name__ == "__main__":
    unittest.main()
