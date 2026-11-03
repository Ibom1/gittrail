"""Build the Gittrail sample in a folder you choose."""

import argparse
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gittrail.git import GitError
from gittrail.sample import build_sample_repo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    folder = parser.parse_args().folder
    try:
        folder.mkdir(parents=True, exist_ok=True)
        build_sample_repo(folder)
    except (GitError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    quoted = shlex.quote(str(folder))
    print(f"Sample repository created in {folder}. Try:")
    print(f"  python -m gittrail log -C {quoted}")
    print(f"  python -m gittrail log --files -C {quoted}")
    print(f"  python -m gittrail file src/hashing.py -C {quoted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
