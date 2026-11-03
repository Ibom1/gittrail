"""Build throwaway git repositories for tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from gittrail.sample import sample_git

# Fixed identity and dates so tests do not depend on the machine's git config.
ENV = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


class Repo:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="gittrail-test-")
        self.path = Path(self._tmp.name)
        self._day = 0
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        env = self._env()
        return sample_git(self.path, *args, date=env["GIT_AUTHOR_DATE"], identity=env)

    def _env(self) -> dict:
        date = f"2026-01-{self._day + 1:02d}T12:00:00+00:00"
        return {**ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}

    def write(self, rel: str, content: str | bytes) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        self._day += 1

    def cleanup(self) -> None:
        self._tmp.cleanup()
