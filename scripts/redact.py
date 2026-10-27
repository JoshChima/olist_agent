"""Redact Terraform output before it reaches a public log or PR comment, then prove it worked.

    terraform plan ... > raw.txt 2>&1; python3 scripts/redact.py < raw.txt

Drops every " [id=...]" (azurerm_client_config's id is the client, object, subscription
and tenant IDs base64-encoded) and replaces every GUID. Then the canary: if the result
still holds an ARM_* value from the environment, the input is withheld and the exit is 1.
GitHub's secret masking can't stand in for this: it only covers logs, and only verbatim.

leaks() is shared with guard_ids.py.
"""

import base64
import binascii
import contextlib
import os
import re
import sys

GUID = re.compile(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
B64 = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,2}")


def redact(text: str) -> str:
    return GUID.sub("<guid>", re.sub(r" \[id=[^]]*\]", "", text))


def leaks(text: str, values: dict[str, str]) -> list[str]:
    """Names of the values found in text: verbatim, as a GUID's first 8 characters, or in base64."""
    seen = [text]
    for token in B64.findall(text):
        token = token.rstrip("=").replace("-", "+").replace("_", "/")
        with contextlib.suppress(binascii.Error, ValueError):
            seen.append(base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "ignore"))
    haystack = "\n".join(seen).lower()
    return [
        name
        for name, value in values.items()
        if value.lower() in haystack or (GUID.fullmatch(value) and value[:8].lower() in haystack)
    ]


if __name__ == "__main__":
    out = redact(sys.stdin.read())
    # ARM_USE_OIDC=true and other flags are too short to be IDs.
    found = leaks(
        out, {k: v for k, v in os.environ.items() if k.startswith("ARM_") and len(v) >= 8}
    )
    if found:
        print(f"redact.py withheld this output: redaction missed {', '.join(found)}. Fix redact().")
        sys.exit(1)
    sys.stdout.write(out)
