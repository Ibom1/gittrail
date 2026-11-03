# Changelog

## v0.2.1

- `gittrail demo` shows Gittrail on a throwaway sample repository.
- `examples/make_sample_repo.py` builds the sample in a folder you choose.

## v0.2.0

- Add `changes <from>..<to>` for release comparisons.
- Add `overview --months N` for repository activity summaries.
- Add `log --since`, `--until`, and `-- <path>` filters.
- Add Markdown output for all four commands.
- Add terminal colors with `--no-color` and `NO_COLOR` controls.
- Omit author metadata from JSON reports.

## v0.1.0

- Summarize Git commits, line counts, and frequently changed files with `gittrail log`.
- Trace individual files across renames with `gittrail file`.
- Export reports as JSON for scripts and other tools.
- Run locally with Python 3.9+ and Git.
