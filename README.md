# gittrail

[![CI](https://github.com/Ibom1/gittrail/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/Ibom1/gittrail/actions/workflows/test.yml)

Read a repository's git history and explain how the code got where it is: which commits changed what, which files change most, and the full timeline of a single file, renames included. Runs locally, needs only Python and git, and never changes your repository.

![Terminal output showing three commits from the Git source repository](docs/demo.svg)

Demo captured against a checkout of the [Git source repository](https://github.com/git/git).

## Who it's for

Developers who join a project, come back to old code, or review a branch and want to know *how* the code got this way, not just what it looks like today. `git log` has the answers, but they're hard to read; gittrail turns them into short, plain summaries.

## What it does (v0.1)

| Command | What it shows |
|---|---|
| `gittrail log [rev]` | Commits newest first, with files changed and lines added / removed, then a summary and the most-changed files |
| `gittrail log --files` | The same, listing every file each commit touched (renames shown as `old -> new`) |
| `gittrail file <path>` | Every commit that touched one file, oldest first, following renames, and every name it was known by |

Options: `-C <repo>` to point at another repository, `-n <count>` to limit commits, `--json` for machine-readable output.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | git failed, or the folder isn't a git repository |
| 64 | Wrong usage |

## How it compares

- **`git log`** gives you the underlying history and flexible filters. Gittrail adds a ready-to-read summary and a ranked list of changed files.
- **tig** lets you browse history interactively in a terminal. Gittrail prints a report you can read, save, or consume as JSON.
- **git-quick-stats** summarizes repository activity. Gittrail focuses on what changed in the code and follows an individual file across renames.

## Install and run

Requires Python 3.9+ and git.

```bash
git clone https://github.com/Ibom1/gittrail.git
cd gittrail
python -m gittrail log -n 5          # run without installing
pip install -e .                     # or install the `gittrail` command
gittrail file README.md
```

## Built with

Python standard library only (`subprocess`, `argparse`, `dataclasses`, `json`). gittrail runs `git log` and parses its output; it never writes to the repository. Tests use `unittest` and build throwaway git repos for each case:

```bash
python -m unittest
```

## Project layout

```
gittrail/git.py      runs git log and parses its output (commits, line counts, renames)
gittrail/history.py  file timelines and log summaries
gittrail/cli.py      the commands and their text / JSON output
tests/               tests on throwaway repositories
```

## License

[MIT](LICENSE)
