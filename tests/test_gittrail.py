import contextlib
import io
import json
import unittest

from gittrail.cli import main
from gittrail.git import GitError, parse_log, parse_numstat_path, read_log, RS, US
from gittrail.history import file_timeline, summarise
from tests.helpers import Repo


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ParseTests(unittest.TestCase):
    def test_plain_path(self):
        self.assertEqual(parse_numstat_path("src/a.py"), ("src/a.py", None))

    def test_simple_rename(self):
        self.assertEqual(parse_numstat_path("old.py => new.py"), ("new.py", "old.py"))

    def test_brace_rename_in_folder(self):
        self.assertEqual(parse_numstat_path("src/{old.py => new.py}"), ("src/new.py", "src/old.py"))

    def test_brace_rename_moves_folder(self):
        self.assertEqual(parse_numstat_path("{lib => src}/a.py"), ("src/a.py", "lib/a.py"))

    def test_brace_rename_into_new_subfolder(self):
        # git writes "{ => sub}" when a file moves into a new sub-folder
        self.assertEqual(parse_numstat_path("src/{ => util}/a.py"), ("src/util/a.py", "src/a.py"))

    def test_binary_and_subject_with_tabs(self):
        out = f"{RS}abc{US}ab{US}Ann{US}2026-01-01T00:00:00+00:00{US}fix\tthing\n\n-\t-\tlogo.png\n3\t1\ta.py\n"
        [c] = parse_log(out)
        self.assertEqual(c.subject, "fix\tthing")
        self.assertTrue(c.files[0].binary)
        self.assertEqual((c.added, c.deleted), (3, 1))


class LogTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_empty_repo_has_no_commits(self):
        self.assertEqual(read_log(self.repo.path), [])
        code, out, _ = run_cli("log", "-C", str(self.repo.path))
        self.assertEqual(code, 0)
        self.assertIn("No commits yet", out)

    def test_commits_newest_first_with_line_counts(self):
        self.repo.write("a.py", "1\n2\n")
        self.repo.commit("first")
        self.repo.write("a.py", "1\n2\n3\n")
        self.repo.write("b.py", "x\n")
        self.repo.commit("second")
        commits = read_log(self.repo.path)
        self.assertEqual([c.subject for c in commits], ["second", "first"])
        self.assertEqual((commits[0].added, commits[0].deleted), (2, 0))
        self.assertEqual(sorted(f.path for f in commits[0].files), ["a.py", "b.py"])

    def test_limit_and_rev(self):
        for i in range(3):
            self.repo.write("a.txt", str(i))
            self.repo.commit(f"c{i}")
        self.assertEqual(len(read_log(self.repo.path, limit=2)), 2)
        self.assertEqual([c.subject for c in read_log(self.repo.path, rev="HEAD~1")], ["c1", "c0"])

    def test_summary_counts_busiest_files(self):
        self.repo.write("a.py", "1")
        self.repo.commit("one")
        self.repo.write("a.py", "2")
        self.repo.write("b.py", "2")
        self.repo.commit("two")
        s = summarise(read_log(self.repo.path))
        self.assertEqual(s.commits, 2)
        self.assertEqual(s.files_touched, 2)
        self.assertEqual(s.busiest_files[0], ("a.py", 2))

    def test_not_a_repository(self):
        plain = Repo()
        try:
            (plain.path / ".git").rename(plain.path / "not-git")
            with self.assertRaises(GitError):
                read_log(plain.path)
            code, _, err = run_cli("log", "-C", str(plain.path))
            self.assertEqual(code, 2)
            self.assertIn("gittrail:", err)
        finally:
            plain.cleanup()

    def test_json_output(self):
        self.repo.write("a.py", "1\n")
        self.repo.commit("only")
        code, out, _ = run_cli("log", "-C", str(self.repo.path), "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["commits"][0]["files"][0]["path"], "a.py")

    def test_bad_usage_exits_64(self):
        self.assertEqual(run_cli("nope")[0], 64)
        self.assertEqual(run_cli("log", "-n", "0", "-C", str(self.repo.path))[0], 64)
        self.assertEqual(run_cli()[0], 64)


class FileTimelineTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_follows_a_rename(self):
        body = "".join(f"line {i}\n" for i in range(20))
        self.repo.write("old.py", body)
        self.repo.commit("add old")
        self.repo.git("mv", "old.py", "new.py")
        self.repo.commit("rename")
        self.repo.write("new.py", body + "more\n")
        self.repo.commit("edit")

        events = file_timeline(self.repo.path, "new.py")
        self.assertEqual([e.kind for e in events], ["created", "renamed", "modified"])
        self.assertEqual(events[0].path, "old.py")
        self.assertEqual(events[1].old_path, "old.py")

        code, out, _ = run_cli("file", "new.py", "-C", str(self.repo.path))
        self.assertEqual(code, 0)
        self.assertIn("Known as: old.py -> new.py", out)

    def test_unknown_file_has_no_history(self):
        self.repo.write("a.py", "1")
        self.repo.commit("one")
        self.assertEqual(file_timeline(self.repo.path, "missing.py"), [])
        self.assertIn("No history found", run_cli("file", "missing.py", "-C", str(self.repo.path))[1])

    def test_never_changes_the_repository(self):
        self.repo.write("a.py", "1")
        self.repo.commit("one")
        before = self.repo.git("status", "--porcelain") + self.repo.git("rev-parse", "HEAD")
        run_cli("log", "-C", str(self.repo.path), "--files")
        run_cli("file", "a.py", "-C", str(self.repo.path))
        after = self.repo.git("status", "--porcelain") + self.repo.git("rev-parse", "HEAD")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
