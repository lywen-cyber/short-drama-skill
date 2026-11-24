#!/usr/bin/env python3
"""positions.py 的回归测试：字位与 count.py 口径一致、--find 定位与退出码。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from positions import find_position, line_positions, main  # noqa: E402
from script_text import count_text  # noqa: E402

POS_PY = SCRIPTS / "positions.py"
SAMPLE = SCRIPTS.parent / "examples" / "授权示范" / "episodes" / "第01集.md"

EPISODE = """第1集

1-1 客厅 夜 内
人物：艾拉、维克

△灯亮着。

维克：签字。

△【音效】门响。

艾拉：我不签。
"""


class PositionsTest(unittest.TestCase):
    def test_total_matches_count(self) -> None:
        rows, total = line_positions(EPISODE)
        self.assertEqual(total, count_text(EPISODE))
        self.assertEqual([r.start for r in rows], [0, 3, 7, 9])

    def test_headers_and_markers_not_counted(self) -> None:
        rows, _ = line_positions(EPISODE)
        texts = [r.text for r in rows]
        self.assertFalse(any("人物" in t or "1-1" in t for t in texts), texts)

    def test_find(self) -> None:
        self.assertEqual(find_position(EPISODE, "我不签"), (9, 14))
        self.assertIsNone(find_position(EPISODE, "不存在的句子"))

    def test_sample_total_and_cli(self) -> None:
        text = SAMPLE.read_text(encoding="utf-8")
        _, total = line_positions(text)
        self.assertEqual(total, count_text(text))
        proc = subprocess.run(
            [sys.executable, str(POS_PY), str(SAMPLE), "--find", "你不够安全"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("第 106 字", proc.stdout)

    def test_find_missing_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "第01集.md"
            f.write_text(EPISODE, encoding="utf-8")
            self.assertEqual(main([str(f), "--find", "没有这句"]), 1)
            self.assertEqual(main([str(f)]), 0)

    def test_missing_path(self) -> None:
        self.assertEqual(main(["/tmp/does-not-exist-positions"]), 1)


if __name__ == "__main__":
    unittest.main()
