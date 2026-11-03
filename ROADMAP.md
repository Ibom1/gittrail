# Roadmap

Gittrail explains code history using local Git data. It runs offline and reads repositories without modifying them. Reports focus on changes to code and omit author names and rankings. Use throwaway repositories to test both cases that trigger a feature and cases that should produce no finding.

| Version | What | Status | Estimate |
|---|---|---|---|
| v0.1 | Read history | ✅ released | |
| v0.2 | Release notes and overview | ✅ released | |
| v0.3 | Summarize branches | not started | 6–8 h |
| v0.4 | Flag changes for review | not started | 5–7 h |
| v0.5 | Find files that change together | not started |6–8 h |
| v0.6 | Trace text and line history | not started |5–7 h |
| v0.7 | Generate an offline report | not started |6–9 h |
| v1.0 | Distribution and scale | not started |8–12 h |

## v0.1 · Read Git history

- [x] Ship commit summaries, line counts, frequently changed files, rename-aware file timelines, and JSON output. See the [changelog](CHANGELOG.md).

**Done when** a throwaway repository produces commit summaries and traces a renamed file in text and JSON.

## v0.2 · Release notes and overview

- [x] Compare revisions with `changes` and summarize repositories with `overview`.
- [x] Add date and path filters to `log`.
- [x] Add Markdown reports and terminal color controls.
- [x] Document examples and troubleshooting.
- [x] Publish after CI passes.

**Done when** tagged snapshots report the same added, removed, and renamed files in text, JSON, and Markdown, and dated fixtures verify overview counts and combined filters.

## v0.3 · Summarize branches

- [ ] Group related branch commits into stories using overlapping paths and commit messages.
- [ ] Export stories with `summary --md` for pull-request descriptions. Generate the Markdown locally from Git history.
- [ ] Offer JSON output for scripts.

**Done when** two unrelated changes form separate stories and Markdown and JSON list the same commits.

## v0.4 · Flag changes for review

- [ ] Prioritize this after branch summaries. Flag large changes without accompanying test changes, frequently changed files, churn, and repeated fixes on the same file.
- [ ] Explain what triggered each flag and support configurable thresholds.

**Done when** each review rule flags its triggering fixture and leaves the control fixture clear.

## v0.5 · Find files that change together

- [ ] Use `together <file>` to show files that often change in the same commit, with counts and percentages.
- [ ] Flag changes that leave a frequently paired file untouched on the branch being reviewed.

**Done when** known pairs report their expected frequency and a branch missing a partner produces a flag.

## v0.6 · Trace text and line history

- [ ] Use `when "text"` to find commits that change the number of occurrences of a string via `git log -S`.
- [ ] Use `file --lines 10,40` to trace a line range via `git log -L`.

**Done when** fixtures identify the commit adding a string and trace changes to a specified line range.

## v0.7 · Generate an offline report

- [ ] Use `report --html` to generate a standalone page with a timeline, hotspots, and charts of files that change together.

**Done when** a generated report opens offline and its counts match the CLI reports.

## Distribution and v1.0

- [x] Check PyPI availability. [Another project uses the `gittrail` distribution name](https://pypi.org/project/gittrail/).
- [ ] Choose and verify a new PyPI distribution name before v1.0. Keep the CLI command `gittrail` and verify installation with `pipx` using the new distribution name.
- [ ] Run CI on Windows, macOS, and Linux.
- [ ] Test performance on repositories with at least 50,000 commits and stream Git output where needed.
- [ ] Continue publishing versioned releases and updating the changelog.

**Done when** a fresh pipx install runs on all three CI platforms and the large-repository fixture completes within the documented performance target.
