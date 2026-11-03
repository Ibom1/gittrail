"""Command-line interface: `gittrail log` and `gittrail file`."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import shlex
import shutil
import tempfile
from pathlib import Path

from . import __version__
from .git import Commit, GitError, read_log
from .history import FileEvent, file_timeline, summarise
from .sample import build_sample_repo
from .reports import changes, markdown_cell, overview, render_report, table

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


def _show_demo(repo: Path) -> None:
    print("Building a sample repository (6 commits, 2 folders, 1 rename, 1 deletion)...")
    build_sample_repo(repo)
    commits = read_log(repo, rev="HEAD")
    path = "src/hashing.py"
    print("\n── Recent history ──")
    print(format_log(commits, show_files=False))
    print("\n── Every file each commit touched ──")
    print(format_log(commits, show_files=True))
    print("\n── One file's story, across a rename ──")
    print(format_timeline(path, file_timeline(repo, path)))
    print("\n── What changed between two releases ──")
    print(render_report("changes", changes(repo, "v0.1", "v0.2"), False))
    print("\n── The whole repo at a glance ──")
    print(render_report("overview", overview(repo, 3), False))
    print("\nThat was a throwaway repository. Try it on your own:")
    print("  gittrail overview -C <path-to-a-repo>")


def _demo(keep: bool) -> int:
    if shutil.which("git") is None:
        print("gittrail demo needs git installed and on PATH", file=sys.stderr)
        return EXIT_ERROR
    try:
        if keep:
            repo = Path(tempfile.mkdtemp(prefix="gittrail-demo-"))
            _show_demo(repo)
            quoted = shlex.quote(str(repo))
            print(f"\nSample repository kept at {repo}")
            print(f"  python -m gittrail log -C {quoted}")
            print(f"  python -m gittrail file src/hashing.py -C {quoted}")
        else:
            with tempfile.TemporaryDirectory(prefix="gittrail-demo-") as folder:
                _show_demo(Path(folder))
    except FileNotFoundError as exc:
        message = "gittrail demo needs git installed and on PATH" if exc.filename == "git" else f"gittrail: {exc}"
        print(message, file=sys.stderr)
        return EXIT_ERROR
    except (GitError, OSError) as exc:
        print(f"gittrail: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gittrail",
        description="Read a repository's git history and explain how the code got where it is.",
    )
    p.add_argument("--version", action="version", version=f"gittrail {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-C", "--repo", default=".", help="repository folder (default: current folder)")
    formats = common.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="print JSON instead of text")
    formats.add_argument("--md", action="store_true", help="print Markdown instead of text")
    common.add_argument("--no-color", action="store_true", help="disable terminal colors")

    lg = sub.add_parser("log", parents=[common], help="list commits with the files and lines they changed")
    lg.add_argument("rev", nargs="?", help="branch, tag or commit to start from (default: HEAD)")
    lg.add_argument("-n", "--limit", type=int, help="show at most this many commits")
    lg.add_argument("--files", action="store_true", help="list each commit's changed files")

    lg.add_argument("--since")
    lg.add_argument("--until")

    ch = sub.add_parser("changes", parents=[common], help="summarize changes between two revisions")
    ch.add_argument("range", metavar="<from>..<to>")
    ov = sub.add_parser("overview", parents=[common], help="summarize repository activity")
    ov.add_argument("--months", type=int, default=12)

    fl = sub.add_parser("file", parents=[common], help="show the timeline of one file, following renames")
    fl.add_argument("path", help="file path, relative to the repository")
    fl.add_argument("rev", nargs="?", help="branch, tag or commit to start from (default: HEAD)")
    demo = sub.add_parser("demo", help="try Gittrail on a sample repository")
    demo.add_argument("--keep", action="store_true", help="keep the sample directory")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    path = None
    try:
        if argv and argv[0] == "log" and "--" in argv:
            boundary = argv.index("--")
            paths = argv[boundary + 1:]
            if len(paths) != 1:
                parser.error("log -- requires exactly one path")
            path = paths[0]
            argv = argv[:boundary]
        args = parser.parse_args(argv)
        if args.command == "changes":
            start, separator, end = args.range.partition("..")
            if not separator or not start or not end or end.startswith(".") or ".." in end:
                parser.error("changes requires <from>..<to>")
        if args.command == "overview" and args.months < 1:
            parser.error("--months must be at least 1")
    except SystemExit as exc:  # argparse exits 2 on bad usage; use 64 like other CLIs
        return EXIT_OK if exc.code == 0 else EXIT_USAGE
    if getattr(args, "limit", None) is not None and args.limit < 1:
        print("gittrail: --limit must be at least 1", file=sys.stderr)
        return EXIT_USAGE

    if args.command == "demo":
        return _demo(args.keep)
    color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ

    def print_text(text):
        if color:
            text = re.sub(r"(?m)^([0-9a-f]{7,})(?=  )", lambda m: f"\x1b[2m{m[0]}\x1b[0m", text)
            text = re.sub(r"(?m)^(  \d{4}-\d{2}-\d{2}  )([0-9a-f]{7,})", lambda m: f"{m[1]}\x1b[2m{m[2]}\x1b[0m", text)
            text = re.sub(r"(?m)^.*(?: -> |  renamed ).*$", lambda m: f"\x1b[33m{m[0]}\x1b[0m", text)
            text = re.sub(r"(?<!\w)([+-])(\d+)\b", lambda m: f"\x1b[{32 if m[1] == '+' else 31}m{m[0]}\x1b[0m", text)
        print(text)

    repo = Path(args.repo)
    try:
        if args.command == "log":
            commits = read_log(repo, rev=args.rev, limit=args.limit, path=path, since=args.since, until=args.until)
            if args.json:
                print(json.dumps({"version": 1, "commits": [commit_to_dict(c) for c in commits]}, indent=2))
            elif args.md:
                rows = [(_day(c.date), c.short, f"{len(c.files)} files", _stat(c.added, c.deleted), c.subject) for c in commits]
                lines = table(["Date", "Commit", "Change", "+/-", "Message"], rows)
                summary = summarise(commits)
                lines.extend(["", f"- {summary.commits} commits, {summary.files_touched} files, {_stat(summary.added, summary.deleted)}"])
                if args.files:
                    for c in commits:
                        for f in c.files:
                            name = f"{f.old_path} → {f.path}" if f.old_path else f.path
                            lines.append(f"- {c.short} · {markdown_cell(name)} · {_stat(f.added, f.deleted)}")
                lines.extend(f"- {markdown_cell(name)} ({count} commits)" for name, count in summary.busiest_files)
                print("\n".join(lines))
            else:
                print_text(format_log(commits, show_files=args.files))
        elif args.command == "file":
            events = file_timeline(repo, args.path, rev=args.rev)
            if args.json:
                print(json.dumps({"version": 1, "path": args.path, "events": [event_to_dict(e) for e in events]}, indent=2))
            elif args.md:
                rows = [(_day(e.commit.date), e.commit.short,
                         f"renamed from {e.old_path}" if e.old_path else e.kind,
                         _stat(e.added, e.deleted), e.commit.subject) for e in events]
                print("\n".join(table(["Date", "Commit", "Change", "+/-", "Message"], rows)
                                + ["", f"- {len(events)} commits for {markdown_cell(args.path)}"]))
            else:
                print_text(format_timeline(args.path, events))
        else:
            report = changes(repo, *args.range.split("..")) if args.command == "changes" else overview(repo, args.months)
            if args.json:
                print(json.dumps({"version": 1, **report}, indent=2))
            elif args.md:
                print(render_report(args.command, report, True))
            else:
                print_text(render_report(args.command, report, False))
    except GitError as exc:
        print(f"gittrail: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
