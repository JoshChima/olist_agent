"""Project SessionStart hook: tell the agent when this checkout is behind origin/main.

A worktree can be cut from a local main that was never fetched, and then every rule
the agent reads (AGENTS.md, docs/agents/) may predate ones that already merged. This
fetches origin/main and, if HEAD is missing commits from it, prints a note that Claude
Code adds to the session's context. Silent when up to date, offline, or outside git.
"""

import os
import subprocess

REPO = os.environ.get("CLAUDE_PROJECT_DIR", ".")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, timeout=20)


try:
    fetched = git("fetch", "-q", "origin", "main").returncode == 0
    behind = git("rev-list", "--count", "HEAD..origin/main").stdout.strip() if fetched else ""
except (OSError, subprocess.TimeoutExpired):
    behind = ""
if behind.isdigit() and int(behind) > 0:
    print(
        f"This checkout is {behind} commit(s) behind origin/main, so AGENTS.md and docs/agents/ "
        "may be missing rules that have merged since. Sync with the base branch before relying "
        "on them, or read them with `git show origin/main:<path>`."
    )
