"""Run git and parse its output into plain Python objects.

Only `git log` is used. gittrail never changes a repository.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# ASCII record and unit separators: they never appear in commit messages,
# so they split git's output safely.
RS = "\x1e"
US = "\x1f"
LOG_FORMAT = f"{RS}%H{US}%h{US}%aI{US}%s"


class GitError(Exception):
    """git failed, or the folder is not a git repository."""


@dataclass
class FileChange:
    path: str
    added: int | None  # None for binary files
    deleted: int | None
    old_path: str | None = None  # set when the file was renamed in this commit

    @property
    def binary(self) -> bool:
        return self.added is None


@dataclass
class Commit:
    sha: str
    short: str
    date: str  # ISO 8601, as git gives it
    subject: str
    files: list[FileChange] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(f.added or 0 for f in self.files)

    @property
    def deleted(self) -> int:
        return sum(f.deleted or 0 for f in self.files)


def run_git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        raise GitError(message[-1] if message else f"git {args[0]} failed")
    return result.stdout


def ensure_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise GitError(f"not a folder: {repo}")
    inside = run_git(repo, "rev-parse", "--is-inside-work-tree").strip()
    if inside != "true":
        raise GitError(f"not a git repository: {repo}")


def has_commits(repo: Path) -> bool:
    try:
        run_git(repo, "rev-parse", "--verify", "HEAD")
        return True
    except GitError:
        return False


# "{old => new}" inside a path, as git prints a rename under --numstat.
_BRACE_RENAME = re.compile(r"\{([^{}]*) => ([^{}]*)\}")


def parse_numstat_path(raw: str) -> tuple[str, str | None]:
    """Return (new_path, old_path) for a --numstat path field.

    git writes renames as either "old => new" or "dir/{old => new}/file".
    """
    match = _BRACE_RENAME.search(raw)
    if match:
        before, after = raw[: match.start()], raw[match.end() :]
        old = (before + match.group(1) + after).replace("//", "/")
        new = (before + match.group(2) + after).replace("//", "/")
        return new, old
    if " => " in raw:
        old, new = raw.split(" => ", 1)
        return new, old
    return raw, None


def parse_log(output: str) -> list[Commit]:
    """Parse `git log --numstat --format=LOG_FORMAT` output."""
    commits: list[Commit] = []
    for record in output.split(RS):
        if not record.strip():
            continue
        header, _, body = record.partition("\n")
        parts = header.split(US)
        if len(parts) != 4:
            continue
        sha, short, date, subject = parts
        commit = Commit(sha, short, date, subject)
        for line in body.splitlines():
            if not line.strip():
                continue
            cols = line.split("\t", 2)
            if len(cols) != 3:
                continue
            added, deleted, raw_path = cols
            path, old = parse_numstat_path(raw_path)
            commit.files.append(
                FileChange(
                    path=path,
                    added=None if added == "-" else int(added),
                    deleted=None if deleted == "-" else int(deleted),
                    old_path=old,
                )
            )
        commits.append(commit)
    return commits


def read_log(
    repo: Path,
    rev: str | None = None,
    limit: int | None = None,
    path: str | None = None,
    follow: bool = False,
) -> list[Commit]:
    """Commits reachable from `rev` (default HEAD), newest first."""
    ensure_repo(repo)
    if not has_commits(repo):
        return []
    args = ["log", "--numstat", "-M", f"--format={LOG_FORMAT}"]
    if limit is not None:
        args.append(f"-n{limit}")
    if follow:
        args.append("--follow")
    if rev:
        args.append(rev)
    if path:
        args += ["--", path]
    return parse_log(run_git(repo, *args))
