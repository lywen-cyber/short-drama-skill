#!/usr/bin/env python3
"""count.py / export_docx.py 口径、扫描与源稿规范化的回归测试。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from count import count_text, is_skippable_line, iter_episode_files  # noqa: E402
from export_docx import export_docx, iter_source_lines  # noqa: E402
from script_text import (  # noqa: E402
    EpisodeScanError,
    count_text_word_approx,
    normalize_source_line,
    tidy_ning_lines,
    validate_episode_files,
)

REPO = SCRIPTS.parent
EXAMPLE = REPO / "examples" / "示例项目"
COUNT_PY = SCRIPTS / "count.py"


def run_count(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COUNT_PY), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class SkipLinesTest(unittest.TestCase):
    def test_episode_titles_are_skipped(self) -> None:
        for line in (
            "第1集",
            "第 1 集",
            "第一集",
            "第01集",
            "第1集 背叛",
            "第 1 集 背叛",
            "第1集：背叛",
            "第1集《背叛》",
            "# 第 1 集（格式占位，不是可交正文）",
            "## 第1集",
        ):
            self.assertTrue(is_skippable_line(line), line)

    def test_scene_headers_are_skipped(self) -> None:
        for line in (
            "1-1 客厅",
            "1-1客厅",
            "1-1　客厅",  # 全角空格
            "1-1-1 回忆",
            "1-1 具体地点  夜  内",
            "### 1-1 客厅 夜 内",
        ):
            self.assertTrue(is_skippable_line(line), repr(line))

    def test_character_lines_half_and_full_colon(self) -> None:
        self.assertTrue(is_skippable_line("人物：女主、男主"))
        self.assertTrue(is_skippable_line("人物:女主、男主"))
        self.assertTrue(is_skippable_line("人物: 【本场实际出现的人】"))

    def test_pure_production_markers_are_skipped(self) -> None:
        for line in ("【闪回】", "【音效】", "【回忆】", "△【闪回】", "【闪回结束】", "【闪回—三年前】"):
            self.assertTrue(is_skippable_line(line), line)

    def test_content_marker_lines_are_not_skipped(self) -> None:
        for line in (
            "【字幕：三年后】",
            "【弹幕1：渣男去死】",
            "【手机短信：老公今晚不回来了】",
            "【新闻：董事会解散】",
        ):
            self.assertFalse(is_skippable_line(line), line)

    def test_body_lines_are_not_skipped(self) -> None:
        self.assertFalse(is_skippable_line("△他推开那扇门。"))
        self.assertFalse(is_skippable_line("姓名：今天就到这里。"))
        self.assertFalse(is_skippable_line("△【音效】大门被撞开，他冲进来。"))
        self.assertFalse(is_skippable_line("**艾拉**（冷笑）：先别走。"))


class CountRulesTest(unittest.TestCase):
    def test_titles_and_headers_not_counted(self) -> None:
        text = "\n".join(
            [
                "第1集 背叛",
                "第一集",
                "第 1 集",
                "第1集：背叛",
                "第1集《背叛》",
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

    def test_markdown_heading_and_bold_normalized_before_count(self) -> None:
        # ### 场头不计；## 集标题不计；**姓名** 只去标记，计对白汉字
        text = "\n".join(
            [
                "## 第1集",
                "### 1-1 客厅 夜 内",
                "人物：艾拉",
                "**艾拉**（冷笑）：先别走。",
            ]
        )
        self.assertEqual(count_text(text), 7)  # 艾拉 + 冷笑 + 先别走
        self.assertEqual(normalize_source_line("**艾拉**（冷笑）："), "艾拉（冷笑）：")
        self.assertEqual(normalize_source_line("### 1-1 客厅 夜 内"), "1-1 客厅 夜 内")
        self.assertEqual(normalize_source_line("## 第1集"), "第1集")

    def test_amount_counts_as_one_word(self) -> None:
        self.assertEqual(count_text("$5,000,000"), 1)
        self.assertEqual(count_text("1,200"), 1)
        self.assertEqual(count_text("30%"), 1)
        self.assertEqual(count_text("支票 $5,000,000 cash"), 2 + 1 + 1)

    def test_production_markers_removed_including_annotated(self) -> None:
        # 【音效】本身不计；「大门被撞开」5 字
        self.assertEqual(count_text("△【音效】大门被撞开"), 5)
        # 整行制作标记不计
        self.assertEqual(count_text("【闪回】\n△他回头。\n【闪回结束】"), 3)
        # 【闪回—三年前】整段去掉，不把「闪回三年前」算进正文；「她站在雨里」5 字
        self.assertEqual(count_text("【闪回—三年前】△她站在雨里。"), 5)

    def test_content_markers_count_inner_text_only(self) -> None:
        self.assertEqual(count_text("【字幕：三年后】"), 3)
        self.assertEqual(count_text("【弹幕1：渣男去死】"), 4)
        self.assertEqual(count_text("【手机短信：老公今晚不回来了】"), 8)
        self.assertEqual(count_text("【新闻：董事会解散】"), 5)
        # 嵌在段里：字幕内文 + 后面的可见描述
        self.assertEqual(count_text("【字幕：三年后】△她站在雨里。"), 3 + 5)

    def test_latin_and_han_default(self) -> None:
        self.assertEqual(count_text("Hello 世界"), 1 + 2)

    def test_word_approx_counts_headers_punct_and_triangle(self) -> None:
        text = "\n".join(
            [
                "第1集",
                "1-1 客厅",
                "人物：艾拉",
                "△他推开门。",
            ]
        )
        pack = count_text(text)
        word = count_text_word_approx(text)
        self.assertEqual(pack, 4)
        self.assertGreater(word, pack)
        # 场头「1-1 客厅」的「客厅」、人物行「人物艾拉」、标题「第1集」、△和句号都应计入近似口径
        self.assertIn("客厅", "1-1 客厅")
        self.assertGreaterEqual(word, pack + 2)


class ScanTest(unittest.TestCase):
    def test_example_project_finds_canonical_episode(self) -> None:
        files = iter_episode_files(EXAMPLE)
        names = [f.name for f in files]
        self.assertEqual(names, ["第01集.md"], names)

    def test_episodes_dir_ignores_drafts_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△正稿。\n", encoding="utf-8")
            (root / "第2集.md").write_text("△根目录旧稿。\n", encoding="utf-8")
            (root / "旧稿").mkdir()
            (root / "旧稿" / "第03集.md").write_text("△子目录草稿。\n", encoding="utf-8")
            (root / "对标笔记").mkdir()
            (root / "对标笔记" / "第3集.md").write_text("△对标笔记。\n", encoding="utf-8")
            files = iter_episode_files(root)
            names = [f.name for f in files]
            self.assertEqual(names, ["第01集.md"], names)

    def test_fallback_only_reads_project_root_not_subdirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "第2集.md").write_text("△根目录。\n", encoding="utf-8")
            (root / "ep03.txt").write_text("△旧文本。\n", encoding="utf-8")
            (root / "旧稿").mkdir()
            (root / "旧稿" / "第01集.md").write_text("△子目录草稿。\n", encoding="utf-8")
            files = iter_episode_files(root)
            names = [f.name for f in files]
            self.assertEqual(names, ["第2集.md", "ep03.txt"], names)

    def test_duplicate_episode_number_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△一。\n", encoding="utf-8")
            (root / "episodes" / "第1集.md").write_text("△重复。\n", encoding="utf-8")
            files = iter_episode_files(root)
            with self.assertRaises(EpisodeScanError) as ctx:
                validate_episode_files(files)
            self.assertIn("同一集号出现两次", str(ctx.exception))
            proc = run_count(str(root))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("同一集号出现两次", proc.stderr)

    def test_missing_and_extra_episodes_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△一。\n", encoding="utf-8")
            (root / "episodes" / "第03集.md").write_text("△三。\n", encoding="utf-8")
            files = iter_episode_files(root)
            with self.assertRaises(EpisodeScanError) as ctx:
                validate_episode_files(files, expected=2)
            msg = str(ctx.exception)
            self.assertIn("缺集", msg)
            self.assertIn("第02集", msg)
            self.assertIn("第03集", msg)
            proc = run_count(str(root), "--episodes", "2")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("缺集", proc.stderr)

    def test_empty_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(iter_episode_files(Path(td)), [])

    def test_out_of_range_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            # 「他推开门」4 字，低于 800
            (root / "episodes" / "第01集.md").write_text("△他推开门。\n", encoding="utf-8")
            proc = run_count(str(root), "--min", "800", "--max", "1000")
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("低于下限", proc.stdout)
            self.assertIn("本包 4", proc.stdout)
            self.assertIn("Word近似", proc.stdout)

    def test_in_range_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△他推开门。\n", encoding="utf-8")
            proc = run_count(str(root), "--min", "1", "--max", "10")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("合格", proc.stdout)


class ExportNormalizeTest(unittest.TestCase):
    def test_headings_and_bold_kept_as_text(self) -> None:
        text = "\n".join(
            [
                "## 第1集",
                "### 1-1 客厅 夜 内",
                "人物：艾拉",
                "**艾拉**（冷笑）：先别走。",
            ]
        )
        lines = iter_source_lines(text)
        self.assertIn("第1集", lines)
        self.assertIn("1-1 客厅 夜 内", lines)
        self.assertIn("人物：艾拉", lines)
        self.assertIn("艾拉（冷笑）：先别走。", lines)
        self.assertFalse(any(line.startswith("#") or "**" in line for line in lines))

    def test_tidy_merges_lone_triangle_and_splits_dialogue(self) -> None:
        merged = tidy_ning_lines(["△", "他推开门。"])
        self.assertEqual(merged, ["△他推开门。"])
        split = tidy_ning_lines(["△她把门关上。艾拉（冷笑）：你走。"])
        self.assertEqual(split, ["△她把门关上。", "艾拉（冷笑）：你走。"])
        self.assertEqual(tidy_ning_lines(["△现在时间：深夜。"]), ["△现在时间：深夜。"])
        self.assertEqual(tidy_ning_lines(["△艾拉（冷笑）：你走。"]), ["艾拉（冷笑）：你走。"])

    def test_export_docx_contains_normalized_headers(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text(
                "## 第1集\n### 1-1 客厅 夜 内\n人物：艾拉\n**艾拉**（冷笑）：先别走。\n",
                encoding="utf-8",
            )
            out = Path(td) / "out.docx"
            export_docx(root, out)
            paras = [p.text for p in Document(str(out)).paragraphs]
            self.assertIn("第1集", paras)
            self.assertIn("1-1 客厅 夜 内", paras)
            self.assertIn("艾拉（冷笑）：先别走。", paras)
            self.assertFalse(any("**" in t or t.startswith("#") for t in paras))

    def test_export_front_prepends_conventional_files(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△正稿动作。\n", encoding="utf-8")
            (root / "creative-plan.md").write_text("大纲占位一行。\n", encoding="utf-8")
            (root / "characters.md").write_text("人物占位一行。\n", encoding="utf-8")
            out = Path(td) / "out.docx"
            export_docx(root, out, front=[])
            paras = [p.text for p in Document(str(out)).paragraphs if p.text.strip()]
            self.assertEqual(paras[0], "大纲占位一行。")
            self.assertEqual(paras[1], "人物占位一行。")
            self.assertIn("△正稿动作。", paras)

    def test_export_ignores_draft_in_subdir(self) -> None:
        from docx import Document

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "episodes").mkdir()
            (root / "episodes" / "第01集.md").write_text("△正稿。\n", encoding="utf-8")
            (root / "旧稿").mkdir()
            (root / "旧稿" / "第02集.md").write_text("△不该出现的草稿。\n", encoding="utf-8")
            out = Path(td) / "out.docx"
            export_docx(root, out)
            paras = [p.text for p in Document(str(out)).paragraphs]
            self.assertIn("△正稿。", paras)
            self.assertFalse(any("不该出现" in t for t in paras))


class AuthorizedSampleTest(unittest.TestCase):
    def test_authorized_sample_pack_count(self) -> None:
        root = REPO / "examples" / "授权示范"
        proc = run_count(str(root), "--min", "730", "--max", "730")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("本包 730", proc.stdout)



if __name__ == "__main__":
    unittest.main()
