"""Command-line interface: `gittrail log` and `gittrail file`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .git import Commit, GitError, read_log
from .history import FileEvent, file_timeline, summarise

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_USAGE = 64


def _stat(added: int | None, deleted: int | None) -> str:
    if added is None:
        return "binary"
    return f"+{added} -{deleted}"


def _day(iso: str) -> str:
    return iso[:10]


# ---------- log ----------


def commit_to_dict(c: Commit) -> dict:
    return {
        "sha": c.sha,
        "short": c.short,
        "author": c.author,
        "date": c.date,
        "subject": c.subject,
        "added": c.added,
        "deleted": c.deleted,
        "files": [
            {"path": f.path, "old_path": f.old_path, "added": f.added, "deleted": f.deleted}
            for f in c.files
        ],
    }


def format_log(commits: list[Commit], show_files: bool) -> str:
    if not commits:
        return "No commits yet."
    lines = []
    for c in commits:
        files = f"{len(c.files)} file{'s' if len(c.files) != 1 else ''}"
        lines.append(f"{c.short}  {_day(c.date)}  {c.subject}")
        lines.append(f"         {files}, +{c.added} -{c.deleted}")
        if show_files:
            for f in c.files:
                name = f"{f.old_path} -> {f.path}" if f.old_path else f.path
                lines.append(f"           {_stat(f.added, f.deleted):>12}  {name}")
    s = summarise(commits)
    lines.append("")
    lines.append(
        f"{s.commits} commit{'s' if s.commits != 1 else ''}, "
        f"{s.files_touched} file{'s' if s.files_touched != 1 else ''} touched, +{s.added} -{s.deleted}"
    )
    if s.busiest_files:
        lines.append("Most changed: " + ", ".join(f"{p} ({n})" for p, n in s.busiest_files))
    return "\n".join(lines)


# ---------- file ----------


def event_to_dict(e: FileEvent) -> dict:
    return {
        "kind": e.kind,
        "path": e.path,
        "old_path": e.old_path,
        "added": e.added,
        "deleted": e.deleted,
        "commit": {"sha": e.commit.sha, "short": e.commit.short, "date": e.commit.date, "subject": e.commit.subject},
    }


def format_timeline(path: str, events: list[FileEvent]) -> str:
    if not events:
        return f"No history found for {path}."
    lines = [f"History of {path}:"]
    for e in events:
        what = {"created": "created", "renamed": "renamed", "modified": "changed"}[e.kind]
        note = f"  (was {e.old_path})" if e.kind == "renamed" else ""
        lines.append(
            f"  {_day(e.commit.date)}  {e.commit.short}  {what:<8} {_stat(e.added, e.deleted):>10}  {e.commit.subject}{note}"
        )
    names = []
    for e in events:
        for n in (e.old_path, e.path):
            if n and n not in names:
                names.append(n)
    lines.append("")
    lines.append(f"{len(events)} commit{'s' if len(events) != 1 else ''}")
    if len(names) > 1:
        lines.append("Known as: " + " -> ".join(names))
    return "\n".join(lines)


# ---------- entry point ----------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gittrail",
        description="Read a repository's git history and explain how the code got where it is.",
    )
    p.add_argument("--version", action="version", version=f"gittrail {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-C", "--repo", default=".", help="repository folder (default: current folder)")
    common.add_argument("--json", action="store_true", help="print JSON instead of text")

    lg = sub.add_parser("log", parents=[common], help="list commits with the files and lines they changed")
    lg.add_argument("rev", nargs="?", help="branch, tag or commit to start from (default: HEAD)")
    lg.add_argument("-n", "--limit", type=int, help="show at most this many commits")
    lg.add_argument("--files", action="store_true", help="list each commit's changed files")

    fl = sub.add_parser("file", parents=[common], help="show the timeline of one file, following renames")
    fl.add_argument("path", help="file path, relative to the repository")
    fl.add_argument("rev", nargs="?", help="branch, tag or commit to start from (default: HEAD)")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 2 on bad usage; use 64 like other CLIs
        return EXIT_OK if exc.code == 0 else EXIT_USAGE
    if getattr(args, "limit", None) is not None and args.limit < 1:
        print("gittrail: --limit must be at least 1", file=sys.stderr)
        return EXIT_USAGE

    repo = Path(args.repo)
    try:
        if args.command == "log":
            commits = read_log(repo, rev=args.rev, limit=args.limit)
            if args.json:
                print(json.dumps({"version": 1, "commits": [commit_to_dict(c) for c in commits]}, indent=2))
            else:
                print(format_log(commits, show_files=args.files))
        elif args.command == "file":
            events = file_timeline(repo, args.path, rev=args.rev)
            if args.json:
                print(json.dumps({"version": 1, "path": args.path, "events": [event_to_dict(e) for e in events]}, indent=2))
            else:
                print(format_timeline(args.path, events))
    except GitError as exc:
        print(f"gittrail: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
