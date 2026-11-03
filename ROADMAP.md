# Roadmap

gittrail turns git history into short, plain explanations of how code got where it is. It runs locally, reads only what `git log` gives it, and never changes a repository.

## Status

| Milestone | Status | Estimate |
|---|---|---|
| v0.1 Read the history (`log`, `file`) | ✅ done | |
| v0.2 Group commits into stories (`summary`) | not started | 6–8 h |
| v0.3 Flag risky changes (`risks`) | not started | 5–7 h |
| v0.4 Optional AI summaries (`--ai`) | not started | 4–6 h |
| v1.0 Ready for everyone | not started | 5–7 h |
| **Total planned** | | **20–28 h** |

## Principles

1. **Read-only.** gittrail never writes to a repository.
2. **Useful without AI.** Every feature works offline; AI is an optional extra layer.
3. **Plain English.** Output a reader understands without knowing git internals.
4. **Standard library first.** No dependencies unless one saves a lot of work.

---

## ✅ v0.1: Read the history

- [x] `gittrail log`: commits with files, lines added / removed, a summary and the most-changed files
- [x] `gittrail file <path>`: one file's timeline, following renames, with every name it had
- [x] Rename parsing for both `old => new` and `dir/{old => new}/file`
- [x] Binary files shown as binary, not as zero lines
- [x] `--json`, `-n`, `-C`, `--files`; exit codes 0 / 2 / 64
- [x] 16 tests on throwaway repos, including "never changes the repository"

## v0.2: Group commits into stories — `gittrail summary` (6–8 h)

**Goal:** explain a branch as a few stories, not a list of 40 commits.

- [ ] `gittrail summary <branch>`: commits on a branch that aren't on the main branch (`main..branch`)
- [ ] Group commits that touch overlapping files within a time window into one "story"
- [ ] Name each story from its most-changed folder and its commit messages ("Mostly in `src/auth/`: 6 commits, +210 −45")
- [ ] Detect common commit-message prefixes (`fix:`, `feat:`, `test:`) and count them
- [ ] `--json` for the stories

**Done when:** on a test repo with two unrelated features developed on one branch, `summary` reports two stories with the right commits in each.

## v0.3: Flag risky changes — `gittrail risks` (5–7 h)

**Goal:** point a reviewer at the changes most worth a careful look.

- [ ] Big change, no tests: a commit adding 200+ lines with no file under `test`/`tests`/`*_test.*`
- [ ] Hotspots: files changed in more than N commits over the last M commits
- [ ] Churn: lines added and removed again within a short span
- [ ] "Fix after fix": several `fix` commits on the same file in a row
- [ ] Each flag says *why* in one sentence; thresholds configurable with flags

**Done when:** each rule has a test repo that triggers it and one that doesn't, and `risks --json` lists the rule id for every flag.

## v0.4: Optional AI summaries — `--ai` (4–6 h)

**Goal:** turn the v0.2 stories into a pull-request description.

- [ ] `gittrail summary <branch> --ai`: send the story data (messages, paths, line counts, **no file contents by default**) to a model and print a short description
- [ ] API key read from the environment or a `.env` file that is git-ignored; `.env.example` with a placeholder
- [ ] `--include-diff` to opt in to sending diffs, with a clear warning
- [ ] Works without the flag exactly as before; tests mock the API call

**Done when:** without an API key, `--ai` exits with a clear message and every other command still works offline.

## v1.0: Ready for everyone (5–7 h)

- [ ] Publish to PyPI so `pipx install gittrail` works
- [ ] CI on Windows, macOS and Linux, Python 3.9–3.13
- [ ] Speed on large repos: test on a repo with 50,000 commits and stream `git log` output instead of loading it all
- [ ] `gittrail file` with `--lines 10,40` to explain the history of a range of lines (via `git log -L`)
- [ ] CHANGELOG and semantic versioning

## Out of scope

- Writing to a repository (rebasing, rewriting, committing)
- Hosting or a web service: gittrail is a local command
- Judging people: no per-author scores or rankings
