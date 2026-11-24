#!/usr/bin/env python3
"""lint.py 的回归测试：说话人、场头、△ 排法、神态词报告与退出码。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lint import (  # noqa: E402
    classify_scene_line,
    lint_path,
    main,
    parse_character_roster,
    speakers_in_line,
)

LINT_PY = SCRIPTS / "lint.py"


CLEAN_EPISODE = """第1集

### 1-1 客厅 夜 内
人物：艾拉、莱恩

△艾拉把合同推到桌沿。

**艾拉**（冷笑）：你签字。

莱恩：我不签。

△莱恩把单子往自己这边拉了一寸。
"""

CLEAN_CHARACTERS = """# 人物小传

## 艾拉（主角）

- 海外稿译名：Ella
- 身份：律师

## 莱恩（对手）

- 短名：Ryan
"""


def write_project(td: str, episode: str, characters: str | None = CLEAN_CHARACTERS, name: str = "第01集.md") -> Path:
    root = Path(td)
    ep_dir = root / "episodes"
    ep_dir.mkdir()
    (ep_dir / name).write_text(episode, encoding="utf-8")
    if characters is not None:
        (root / "characters.md").write_text(characters, encoding="utf-8")
    return root


def run_lint(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_PY), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class HelpersTest(unittest.TestCase):
    def test_valid_header_after_heading_hash(self) -> None:
        # classify 用的是规范化后的行；这里直接测规范化后的结果
        from script_text import normalize_source_line

        self.assertEqual(classify_scene_line(normalize_source_line("### 1-1 客厅 夜 内")), "valid")
        self.assertEqual(classify_scene_line("1-1 客厅 夜 内"), "valid")
        self.assertEqual(classify_scene_line("1-1-1 回忆"), "valid")

    def test_invalid_headers(self) -> None:
        self.assertEqual(classify_scene_line("1.1 客厅 夜 内"), "invalid")
        self.assertEqual(classify_scene_line("客厅 夜 内"), "invalid")
        self.assertEqual(classify_scene_line("第一场 客厅 夜 内"), "invalid")
        self.assertEqual(classify_scene_line("场头：客厅 夜 内"), "invalid")

    def test_action_not_treated_as_header(self) -> None:
        self.assertEqual(classify_scene_line("△夜风灌进室内。"), "other")

    def test_speakers_ignore_time_label(self) -> None:
        self.assertEqual(speakers_in_line("△现在时间：深夜。"), [])
        self.assertEqual(speakers_in_line("艾拉（冷笑）：签字。"), ["艾拉"])
        self.assertEqual(speakers_in_line("△艾拉：签字。"), ["艾拉"])

    def test_roster_from_headings_and_short_names(self) -> None:
        names = parse_character_roster(CLEAN_CHARACTERS)
        self.assertIn("艾拉", names)
        self.assertIn("莱恩", names)
        self.assertIn("Ella", names)
        self.assertIn("Ryan", names)
        self.assertNotIn("人物小传", names)


class LintRulesTest(unittest.TestCase):
    def test_clean_episode_has_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, CLEAN_EPISODE)
            issues, manner, chars = lint_path(root)
            self.assertEqual(issues, [], [i.format() for i in issues])
            self.assertIsNotNone(chars)
            self.assertGreaterEqual(manner["冷笑"], 1)

    def test_speaker_not_in_scene_cast(self) -> None:
        ep = CLEAN_EPISODE.replace("人物：艾拉、莱恩", "人物：莱恩")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            msgs = [i.message for i in issues]
            self.assertTrue(any("艾拉" in m and "本场人物表" in m for m in msgs), msgs)

    def test_speaker_not_in_characters(self) -> None:
        ep = CLEAN_EPISODE.replace("人物：艾拉、莱恩", "人物：艾拉、莱恩、琼斯")
        ep = ep.replace("莱恩：我不签。", "琼斯：我不签。")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            msgs = [i.message for i in issues]
            self.assertTrue(any("琼斯" in m and "人物小传" in m for m in msgs), msgs)

    def test_no_characters_file_skips_roster_check(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, CLEAN_EPISODE, characters=None)
            issues, _, chars = lint_path(root)
            self.assertIsNone(chars)
            self.assertEqual(issues, [], [i.format() for i in issues])

    def test_malformed_scene_header(self) -> None:
        ep = CLEAN_EPISODE.replace("### 1-1 客厅 夜 内", "1.1 客厅 夜 内")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertTrue(any("场头无法识别" in i.message for i in issues), [i.message for i in issues])

    def test_lone_triangle(self) -> None:
        ep = CLEAN_EPISODE.replace("△艾拉把合同推到桌沿。", "△\n艾拉把合同推到桌沿。")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertTrue(any("△ 单独成行" in i.message for i in issues), [i.message for i in issues])

    def test_triangle_squeezed_with_dialogue(self) -> None:
        ep = CLEAN_EPISODE.replace(
            "△艾拉把合同推到桌沿。\n\n**艾拉**（冷笑）：你签字。",
            "△艾拉把合同推到桌沿。艾拉（冷笑）：你签字。",
        )
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertTrue(any("△ 与对白挤在同一段" in i.message for i in issues), [i.message for i in issues])

    def test_dialogue_mentioning_triangle_is_not_squeezed(self) -> None:
        ep = CLEAN_EPISODE.replace(
            "莱恩：我不签。",
            "莱恩：对白不要与 △ 挤在同一段。",
        )
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertFalse(
                any("△ 与对白挤在同一段" in i.message for i in issues),
                [i.message for i in issues],
            )

    def test_pronoun_speaker(self) -> None:
        ep = CLEAN_EPISODE.replace("莱恩：我不签。", "他：我不签。")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertTrue(any("说话人写成「他」" in i.message for i in issues), [i.message for i in issues])

    def test_missing_cast_line(self) -> None:
        ep = CLEAN_EPISODE.replace("人物：艾拉、莱恩\n\n", "")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            issues, _, _ = lint_path(root)
            self.assertTrue(any("没有人物行" in i.message for i in issues), [i.message for i in issues])

    def test_mannerisms_do_not_fail_clean_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, CLEAN_EPISODE)
            issues, manner, _ = lint_path(root)
            self.assertEqual(issues, [])
            self.assertGreaterEqual(manner["冷笑"], 1)
            proc = run_lint(str(root))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("神态词统计", proc.stdout)
            self.assertIn("冷笑", proc.stdout)

    def test_issues_exit_nonzero(self) -> None:
        ep = CLEAN_EPISODE.replace("△艾拉把合同推到桌沿。", "△")
        with tempfile.TemporaryDirectory() as td:
            root = write_project(td, ep)
            proc = run_lint(str(root))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("△ 单独成行", proc.stdout)

    def test_main_missing_path(self) -> None:
        self.assertEqual(main(["/tmp/does-not-exist-lint-skill"]), 1)


if __name__ == "__main__":
    unittest.main()
