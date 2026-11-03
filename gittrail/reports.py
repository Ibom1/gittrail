"""Read-only release and repository reports."""
from collections import Counter
from pathlib import PurePosixPath

from .git import GitError, ensure_repo, read_log, run_git


def changes(repo, start, end):
    ensure_repo(repo)
    revisions = []
    for rev in (start, end):
        try:
            revisions.append(run_git(repo, "rev-parse", "--verify", "--end-of-options", rev + "^{commit}").strip())
        except GitError as exc:
            raise GitError(f"unknown revision: {rev}") from exc
    base, tip = revisions
    args = ("diff", "--no-ext-diff", "-M")
    entries = iter(run_git(repo, *args, "--name-status", "-z", base, tip).split("\0"))
    files = []
    for status in entries:
        if not status:
            break
        path = next(entries)
        old_path = path if status.startswith("R") else None
        files.append(dict(status=status[0], path=next(entries) if old_path else path, old_path=old_path))
    stats = iter(run_git(repo, *args, "--numstat", "-z", base, tip).split("\0"))
    by_path = {}
    for entry in stats:
        if not entry:
            break
        added, deleted, path = entry.split("\t", 2)
        if not path:
            next(stats)
            path = next(stats)
        by_path[path] = (None if added == "-" else int(added), None if deleted == "-" else int(deleted))
    commits = read_log(repo, rev=f"{base}..{tip}")
    counts = Counter(path for c in commits for path in {f.path for f in c.files})
    folders = {}
    for file in files:
        path = file["path"]
        file["added"], file["deleted"] = by_path[path]
        file["commits"] = counts[path]
        folder = folders.setdefault(folder_name(path), dict(files=0, added=0, deleted=0))
        folder["files"] += 1
        folder["added"] += file["added"] or 0
        folder["deleted"] += file["deleted"] or 0
    return dict(start=start, end=end, commits=len(commits), files=files, folders=folders,
                added=sum(x["added"] for x in folders.values()), deleted=sum(x["deleted"] for x in folders.values()))


def folder_name(path):
    parts = PurePosixPath(path).parts
    return parts[0] + "/" if len(parts) > 1 else "(root)"


def overview(repo, months):
    commits = read_log(repo)
    days = sorted(c.date[:10] for c in commits)
    folders = Counter(folder for c in commits for folder in {folder_name(f.path) for f in c.files})
    files = Counter(path for c in commits for path in {f.path for f in c.files})
    counts = Counter(day[:7] for day in days)
    timeline = {}
    if days:
        year, month = map(int, days[-1][:7].split("-"))
        latest = year * 12 + month - 1
        for index in range(max(12, latest - months + 1), latest + 1):
            y, m = divmod(index, 12)
            label = f"{y:04d}-{m + 1:02d}"
            timeline[label] = counts[label]
    return dict(commits=len(commits), first=days[0] if days else None, last=days[-1] if days else None,
                months=timeline, folders=dict(folders.most_common(5)), files=dict(files.most_common(5)))


def markdown_cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ")


def table(headers, rows):
    return ["| " + " | ".join(map(markdown_cell, row)) + " |" for row in
            [headers, ["---"] * len(headers), *rows]]


def render_report(command, data, markdown):
    heading = (lambda title: "### " + title) if markdown else (lambda title: title)
    bullet = "- " if markdown else "  "
    if command == "changes":
        start, end = data["start"], data["end"]
        files = data["files"]
        if not files:
            return f"No changes between {start} and {end}"
        lines = [heading(f"Changes from {start} to {end}: {data['commits']} commits, {len(files)} files, +{data['added']} -{data['deleted']}")]
        for label, status in (("Added", "A"), ("Renamed", "R"), ("Removed", "D"), ("Modified", "M"), ("Type changed", "T")):
            paths = [f"{f['old_path']} -> {f['path']}" if f["old_path"] else f["path"] for f in files if f["status"] == status]
            lines.append(f"{bullet}{label} ({len(paths)})  " + ", ".join(map(markdown_cell if markdown else str, paths)))
        lines.extend(["", heading("By folder")])
        lines.extend(f"{bullet}{p}  {n['files']} files  +{n['added']} -{n['deleted']}" for p, n in sorted(data["folders"].items()))
        lines.extend(["", heading("Most changed")])
        for file in sorted(files, key=lambda f: (-f["commits"], f["path"]))[:5]:
            stat = "binary" if file["added"] is None else f"+{file['added']} -{file['deleted']}"
            lines.append(f"{bullet}{file['path']}  {file['commits']} commits  {stat}")
        return "\n".join(lines)
    if not data["commits"]:
        return "No commits yet"
    lines = [heading(f"Repository: {data['commits']} commits, {data['first']} to {data['last']}")]
    if data["commits"] > 1:
        peak = max(data["months"].values(), default=0)
        lines.extend(["", heading(f"Commits per month (last {len(data['months'])})")])
        for month, count in data["months"].items():
            bar = "█" * max(1, round(24 * count / peak)) if count else ""
            lines.append(f"{bullet}{month}  {count}" if markdown else f"{bullet}{month}  {bar:24}  {count}")
    for title, key in (("Busiest folders", "folders"), ("Most changed files", "files")):
        lines.extend(["", heading(title)])
        lines.extend(f"{bullet}{p}  {n} commits" for p, n in data[key].items())
    return "\n".join(lines)
