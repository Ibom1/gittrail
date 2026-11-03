"""Build a deterministic sample history in an empty directory."""

import os
import subprocess
from pathlib import Path

from .git import GitError


def sample_git(path: Path, *args: str, date: str = "", identity: dict = None) -> str:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    env.update(identity or {})
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    result = subprocess.run(["git", "-C", str(path), *args], env=env,
                            capture_output=True, text=True)
    if result.returncode:
        raise GitError(result.stderr.strip() or "git command failed")
    return result.stdout


def build_sample_repo(path: Path) -> None:
    if any(path.iterdir()):
        raise GitError(f"Folder is not empty: {path}")
    sample_git(path, "init", "-q", "-b", "main", "--template=")
    sample_git(path, "config", "--local", "user.name", "Sample Dev")
    sample_git(path, "config", "--local", "user.email", "sample@example.com")
    sample_git(path, "config", "--local", "core.autocrlf", "false")

    def write(name, content):
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))

    def commit(day, message):
        sample_git(path, "add", "-A")
        sample_git(path, "commit", "-q", "-m", message, date=f"2026-01-{day:02}T10:00:00Z")

    write("README.md", "# Sample project\n")
    write("src/app.py", "def main():\n    return 'Sample project'\n")
    commit(5, "Add project skeleton")
    hashing = '''"""Calculate checksums for local sample files."""

import hashlib
from pathlib import Path


DEFAULT_ALGORITHM = "sha256"
BLOCK_SIZE = 4096


def hash_bytes(data, algorithm=DEFAULT_ALGORITHM):
    """Return the hexadecimal digest of bytes."""
    digest = hashlib.new(algorithm)
    digest.update(data)
    return digest.hexdigest()


def hash_file(path, algorithm=DEFAULT_ALGORITHM):
    """Read a file in blocks and return its hexadecimal digest."""
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        block = stream.read(BLOCK_SIZE)
        while block:
            digest.update(block)
            block = stream.read(BLOCK_SIZE)
    return digest.hexdigest()


def same_contents(first, second):
    """Compare two files using their digests."""
    return hash_file(first) == hash_file(second)
'''
    write("src/hash.py", hashing)
    commit(8, "Add hashing module")
    write("src/config.py", "def load_config():\n    return {}\n")
    write("tests/test_app.py", "from src.app import main\n\ndef test_main():\n    assert main() == 'Sample project'\n")
    commit(10, "Add config loader and tests")
    sample_git(path, "tag", "v0.1")
    sample_git(path, "mv", "src/hash.py", "src/hashing.py")
    commit(14, "Rename hash module")
    write("src/hashing.py", hashing.replace("4096", "65536"))
    write("tests/test_app.py", (path / "tests/test_app.py").read_text() +
          "\n\ndef test_hash():\n    from src.hashing import hash_bytes\n    assert len(hash_bytes(b'sample')) == 64\n")
    commit(17, "Improve hashing speed")
    (path / "src/config.py").unlink()
    commit(20, "Remove old config loader")
    sample_git(path, "tag", "v0.2")
