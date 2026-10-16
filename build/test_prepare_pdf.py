"""Check PDF metadata isolation, document links, and diagram preprocessing."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("prepare_pdf", Path(__file__).with_name("prepare-pdf.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparePdfTest(unittest.TestCase):
    def setUp(self):
        self.previous = Path.cwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def test_metadata_links_and_code(self):
        Path("章").mkdir()
        Path("章/一.md").write_text(
            "---\ntitle: 最后章节\n---\n# 章节\n✅\n"
            "[目录](../README.md) [同章](二.md#中文) [本页](#标题)\n"
            "```text\n[原样](二.md)\n```\n"
        )
        module.prepare(["章/一.md"], "tmp/book.md", "unused")
        text = Path("tmp/book.md").read_text()
        self.assertNotIn("title:", text)
        self.assertIn("[通过]", text)
        self.assertIn("https://oh-my-vibe-coding.github.io/ai-reliability-architecture/)", text)
        self.assertIn("/%E7%AB%A0/%E4%BA%8C/#中文)", text)
        self.assertIn("/%E7%AB%A0/%E4%B8%80/#标题)", text)
        self.assertIn("```text\n[原样](二.md)\n```", text)

    @patch.object(module.subprocess, "run")
    def test_diagram_is_rendered_once_without_rewriting_labels(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        code = "flowchart LR\n A[① 缓存] --> B[✅]\n"
        Path("a.md").write_text(f"# A\n```mermaid\n{code}```\n\n```mermaid\n{code}```\n")
        module.prepare(["a.md"], "tmp/book.md", "mmdc", "browser.json")
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertEqual(Path(command[command.index("-i") + 1]).read_text(), code)
        self.assertIn("--size", command)
        self.assertEqual(command[-2:], ["-p", "browser.json"])
        self.assertEqual(Path("tmp/book.md").read_text().count("![架构图]"), 2)

    @patch.object(module.subprocess, "run")
    def test_renderer_failure_stops_publication(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "bad diagram")
        Path("a.md").write_text("```mermaid\ninvalid\n```\n")
        with self.assertRaisesRegex(RuntimeError, "bad diagram"):
            module.prepare(["a.md"], "tmp/book.md", "mmdc")
        self.assertFalse(Path("tmp/book.md").exists())


if __name__ == "__main__":
    unittest.main()
