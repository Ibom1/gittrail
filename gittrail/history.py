"""Turn parsed commits into the views gittrail shows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .git import Commit, read_log


@dataclass
class FileEvent:
    commit: Commit
    path: str  # the file's name in this commit
    old_path: str | None  # its previous name, when this commit renamed it
    added: int | None
    deleted: int | None
    kind: str  # "created", "modified" or "renamed"


def file_timeline(repo: Path, path: str, rev: str | None = None) -> list[FileEvent]:
    """Every commit that touched `path`, oldest first, following renames."""
    commits = read_log(repo, rev=rev, path=path, follow=True)
    events: list[FileEvent] = []
    for commit in reversed(commits):  # oldest first
        # With --follow and a path, git limits numstat to this file.
        change = commit.files[0] if commit.files else None
        if change is None:
            continue
        if not events:
            kind = "created"
        elif change.old_path:
            kind = "renamed"
        else:
            kind = "modified"
        events.append(
            FileEvent(commit, change.path, change.old_path, change.added, change.deleted, kind)
        )
    return events


@dataclass
class LogSummary:
    commits: int
    added: int
    deleted: int
    files_touched: int
    busiest_files: list[tuple[str, int]]  # (path, number of commits), most first


def summarise(commits: list[Commit], top: int = 5) -> LogSummary:
    touches: Counter[str] = Counter()
    for c in commits:
        for f in c.files:
            touches[f.path] += 1
    busiest = sorted(touches.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return LogSummary(
        commits=len(commits),
        added=sum(c.added for c in commits),
        deleted=sum(c.deleted for c in commits),
        files_touched=len(touches),
        busiest_files=busiest,
    )
