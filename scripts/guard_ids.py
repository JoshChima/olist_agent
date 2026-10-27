"""Project PreToolUse hook: agents can't post a known Azure ID to GitHub or Linear.

The repo is public, and agents post under the user's account. This checks the text of
`gh pr|issue|api|release|gist` commands (and any --body-file / -F @file they read) and
of MCP write tools (save_*, create_*, update_*, add_*, ...). The known IDs are the repo's
GitHub variables, the ones tf-toolbox.sh reads, which only collaborators can see. Matching
is redact.leaks(): verbatim, a GUID's first 8 characters, or base64-encoded.

Exit 2 blocks the call and names the variable that matched, never its value. If the IDs
can't be loaded, every checked call is blocked: fail closed, like the apply gate.
OLIST_KNOWN_IDS ({"NAME": "value"} JSON) replaces the gh lookup; test_guards.py uses it.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from redact import leaks

REPO = Path(__file__).resolve().parent.parent
GH_IDS = ["gh", "variable", "list", "--json", "name,value", "-q", "map({(.name): .value}) | add"]
GH_POST = re.compile(r"\bgh\s+(pr|issue|api|release|gist)\b")
BODY_FILE = re.compile(r"(?:--body-file|-F)[ =]+(?:\w+=)?@?(\"[^\"]*\"|'[^']*'|\S+)")
MCP_WRITE = re.compile(r"^mcp__.*__(save|create|update|add|push|reply|submit|merge)_|_write$")


def block(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(2)  # 2 = block; sys.exit("msg") would exit 1, which only warns


call = json.load(sys.stdin)
tool, args = call.get("tool_name", ""), call.get("tool_input", {})
if tool == "Bash":
    command = args.get("command", "")
    if not GH_POST.search(command):
        sys.exit(0)
    text = command
    for path in BODY_FILE.findall(command):
        file = Path(call.get("cwd") or ".", path.strip("\"'"))
        if file.is_file():
            text += "\n" + file.read_text(encoding="utf-8", errors="replace")
elif MCP_WRITE.search(tool):
    text = json.dumps(args, ensure_ascii=False)
else:
    sys.exit(0)

try:
    known = (
        os.environ.get("OLIST_KNOWN_IDS")
        or subprocess.run(
            GH_IDS, cwd=REPO, capture_output=True, text=True, check=True, timeout=30
        ).stdout
    )
    values = {k: v for k, v in json.loads(known).items() if len(v) >= 8}
except Exception as e:  # noqa: BLE001 - any failure means we can't vouch for the text
    block(
        f"Blocked: couldn't load the repo's known IDs to check this text ({type(e).__name__}). "
        "Check `gh auth status` in the repo, then retry."
    )

found = leaks(text, values)
if found:
    block(
        f"Blocked: this text contains the value of {', '.join(found)} (verbatim, as a prefix, "
        "or base64-encoded), and it would be public. Remove or redact it, then retry."
    )
