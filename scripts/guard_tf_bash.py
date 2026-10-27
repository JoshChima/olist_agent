"""PreToolUse hook for the terraform-operator subagent: Bash may only run scripts/tf-toolbox.sh.

Claude Code passes the tool call as JSON on stdin. Exit 2 blocks the call and shows
stderr to the subagent. Keeping one exact command form also guarantees the
`ask` rule for `scripts/tf-toolbox.sh apply` in .claude/settings.json always matches.
"""

import json
import re
import sys

ALLOWED = re.compile(
    r"scripts/tf-toolbox\.sh (up|login|whoami|down"
    r"|check (bootstrap|infra)( --offline)?|plan (bootstrap|infra)"
    r"|apply bootstrap /tmp/plans/bootstrap\.tfplan [0-9a-f]{64})"
)

command = json.load(sys.stdin).get("tool_input", {}).get("command", "").strip()
if not ALLOWED.fullmatch(command):
    print(
        f"Blocked: {command!r}. This agent may only run "
        "`scripts/tf-toolbox.sh up|login|whoami|down|check <root> [--offline]|plan <root>`"
        " or `scripts/tf-toolbox.sh apply bootstrap /tmp/plans/bootstrap.tfplan <sha256>`,"
        " from the repo root, with nothing chained. Use Read/Grep/Glob for files.",
        file=sys.stderr,
    )
    sys.exit(2)  # 2 = block; sys.exit("msg") would exit 1, which only warns
