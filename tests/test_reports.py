"""Exercise reports through the CLI against disposable repositories."""
import io
import json
import unittest
from html import unescape
from unittest.mock import patch

from gittrail.cli import main
from tests.helpers import Repo
from tests.test_gittrail import run_cli


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)

    def run_report(self, *args):
        return run_cli(*args, "-C", str(self.repo.path))

    def test_release_diff(self):
        self.repo.write("old.txt", "keep\n")
        self.repo.write("remove.txt", "remove\n")
        self.repo.commit("base")
        self.repo.git("tag", "v1")
        self.repo.git("mv", "old.txt", "new.txt")
        self.repo.git("rm", "remove.txt")
        self.repo.write("src/add.txt", "add\n")
        self.repo.commit("release")
        self.repo.git("tag", "v2")
        code, out, _ = self.run_report("changes", "v1..v2", "--json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(report["commits"], 1)
        self.assertEqual((report["added"], report["deleted"]), (1, 1))
        self.assertEqual({(f["status"], f["path"], f["old_path"]) for f in report["files"]},
                         {("A", "src/add.txt", None), ("D", "remove.txt", None), ("R", "new.txt", "old.txt")})
        for flags in ((), ("--md",)):
            out = self.run_report("changes", "v1..v2", *flags)[1]
            for item in ("src/add.txt", "remove.txt", "old.txt -> new.txt"):
                self.assertIn(item, unescape(out))
        self.assertIn("No changes between", self.run_report("changes", "v1..v1")[1])
        code, _, err = self.run_report("changes", "v1..v9")
        self.assertEqual(code, 2)
        self.assertIn("unknown revision: v9", err)
        self.assertEqual(self.run_report("changes", "v1")[0], 64)

    def test_overview_and_filters(self):
        self.assertEqual(self.run_report("overview")[1].strip(), "No commits yet")
        for month in (1, 2, 3):
            date = f"2026-{month:02d}-10T12:00:00+00:00"
            env = {**self.repo._env(), "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
            with patch.object(self.repo, "_env", return_value=env):
                folder = "src" if month != 2 else "tests"
                self.repo.write(f"{folder}/file.txt", str(month))
                self.repo.commit(f"month {month}")
            if month == 1:
                self.assertNotIn("Commits per month", self.run_report("overview")[1])
        data = json.loads(self.run_report("overview", "--months", "3", "--json")[1])
        self.assertEqual(data["months"], {"2026-01": 1, "2026-02": 1, "2026-03": 1})
        self.assertEqual(data["files"]["src/file.txt"], 2)
        # Put repository options before Git's path separator.
        code, text, _ = run_cli("log", "-C", str(self.repo.path), "--since", "2026-01-01",
                                "--until", "2026-02-28", "-n", "1", "--md", "--", "src/")
        self.assertEqual(code, 0)
        self.assertTrue(text.startswith("| Date | Commit |"))
        self.assertIn("month 1", text)
        self.assertNotIn("month 2", text)
        self.assertNotIn("month 3", text)
        self.assertEqual(self.run_report("log", "--md", "--json")[0], 64)
        self.assertTrue(self.run_report("file", "src/file.txt", "--md")[1].startswith("| Date | Commit |"))

    def test_terminal_color(self):
        self.repo.write("a.txt", "one\n")
        self.repo.commit("add")
        self.assertNotIn("\x1b[", self.run_report("log")[1])
        for env, flags, expected in (({}, [], True), ({"NO_COLOR": ""}, [], False),
                                     ({}, ["--no-color"], False), ({}, ["--md"], False)):
            out = io.StringIO()
            with patch.dict("os.environ", env, clear=False), patch("sys.stdout", out), patch.object(out, "isatty", return_value=True):
                if not env:
                    with patch.dict("os.environ") as environ:
                        environ.pop("NO_COLOR", None)
                        self.assertEqual(main(["log", "-C", str(self.repo.path), *flags]), 0)
                else:
                    self.assertEqual(main(["log", "-C", str(self.repo.path), *flags]), 0)
            self.assertEqual("\x1b[" in out.getvalue(), expected)
