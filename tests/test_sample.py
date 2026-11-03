"""Verify the shared history and the demo's temporary directory behavior."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gittrail.git import read_log
from gittrail.sample import build_sample_repo, sample_git
from tests.test_gittrail import run_cli


class SampleTests(unittest.TestCase):
    def test_history_and_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            build_sample_repo(path)
            self.assertEqual([commit.subject for commit in read_log(path)], [
                "Remove old config loader", "Improve hashing speed", "Rename hash module",
                "Add config loader and tests", "Add hashing module", "Add project skeleton",
            ])
            self.assertEqual(sample_git(path, "tag").splitlines(), ["v0.1", "v0.2"])
            code, out, _ = run_cli("file", "src/hashing.py", "-C", folder)
            self.assertEqual(code, 0)
            for expected in ("created", "renamed", "(was src/hash.py)", "changed",
                             "Known as: src/hash.py -> src/hashing.py"):
                self.assertIn(expected, out)

    def test_demo_cleans_up_without_changing_directory(self):
        cwd = Path.cwd()
        with patch("gittrail.cli.build_sample_repo", wraps=build_sample_repo) as build:
            code, out, _ = run_cli("demo")
        self.assertEqual(code, 0)
        for expected in ("── Recent history ──", "── Every file each commit touched ──",
                         "── One file's story, across a rename ──",
                         "Known as: src/hash.py -> src/hashing.py"):
            self.assertIn(expected, out)
        self.assertFalse(build.call_args.args[0].exists())
        self.assertEqual(Path.cwd(), cwd)

    def test_demo_keep(self):
        with patch("gittrail.cli.build_sample_repo", wraps=build_sample_repo) as build:
            code, out, _ = run_cli("demo", "--keep")
        path = build.call_args.args[0]
        self.addCleanup(shutil.rmtree, path)
        self.assertEqual(code, 0)
        self.assertIn(str(path), out)
        self.assertTrue((path / ".git").is_dir())

    def test_demo_requires_git(self):
        with patch("gittrail.cli.shutil.which", return_value=None):
            code, _, err = run_cli("demo")
        self.assertEqual(code, 2)
        self.assertIn("gittrail demo needs git installed and on PATH", err)

    def test_example_script_refuses_to_overwrite(self):
        import subprocess
        import sys

        script = Path(__file__).resolve().parents[1] / "examples" / "make_sample_repo.py"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample repo"
            command = [sys.executable, str(script), str(path)]
            created = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertIn("Sample repository created in", created.stdout)
            self.assertEqual(len(read_log(path)), 6)
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertIn(f"Folder is not empty: {path}", repeated.stderr)
