"""Project PreToolUse hook: every `tf-toolbox.sh apply` needs a person's approval.

Backs up the `ask` permission rule in .claude/settings.json. A live test showed that
the rule alone didn't prompt, so this hook asks explicitly, for every agent and in
every mode. Everything else passes through untouched.
"""

import json
import re
import sys

command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
if re.search(r"tf-toolbox\.sh\s+apply\b", command):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": "Terraform apply against real Azure: "
                    "check that the sha256 matches the plan you reviewed.",
                }
            }
        )
    )
