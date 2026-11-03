# Roadmap

Gittrail explains code history using local Git data. It runs offline and reads repositories without modifying them. Reports focus on changes to code and omit author names and rankings. Use throwaway repositories to test both cases that trigger a feature and cases that should produce no finding.

## v0.1 · Read Git history

Released with commit summaries, line counts, frequently changed files, rename-aware file timelines, and JSON output. See the [changelog](CHANGELOG.md).

## v0.2 · Summarize branches

- Group related branch commits into stories using overlapping paths and commit messages.
- Export stories with `summary --md` for pull-request descriptions. Generate the Markdown locally from Git history.
- Offer JSON output for scripts.

## v0.3 · Flag changes for review

- Prioritize this after branch summaries. Flag large changes without accompanying test changes, frequently changed files, churn, and repeated fixes on the same file.
- Explain what triggered each flag and support configurable thresholds.

## v0.4 · Find files that change together

- Use `together <file>` to show files that often change in the same commit, with counts and percentages.
- Flag changes that leave a frequently paired file untouched on the branch being reviewed.

## v0.5 · Trace text and line history

- Use `when "text"` to find commits that change the number of occurrences of a string via `git log -S`.
- Use `file --lines 10,40` to trace a line range via `git log -L`.

## v0.6 · Generate an offline report

- Use `report --html` to generate a standalone page with a timeline, hotspots, and charts of files that change together.

## Distribution and v1.0

- Start PyPI packaging and name availability checks early. Publish once ownership and release credentials are set up, then verify `pipx install gittrail`.
- Run CI on Windows, macOS, and Linux.
- Test performance on repositories with at least 50,000 commits and stream Git output where needed.
- Continue publishing versioned releases and updating the changelog.
