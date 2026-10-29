"""Self-check that `tf-toolbox.sh apply` refuses unless the risk gate says go (ADR-0007).

Run: python3 scripts/test_tf_toolbox.py. Fake `docker` and `gh` go first on PATH. The
fake docker runs each `docker exec` command on the host, where a fake `terraform`
prints a scripted `show -json` and logs any `apply`, and the real tf_risk.py judges it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).parent

# Git Bash on Windows, bash elsewhere. System32's bash is WSL, which can't run this.
BASH = shutil.which("bash")
if not BASH or "system32" in BASH.lower():
    print("tf-toolbox: skipped, no bash on PATH (run from Git Bash)")
    sys.exit(0)

FAKES = {
    # Skip exec's flags up to the container name, then run the command here.
    "docker": """case "$1" in
inspect) echo true ;;
exec)
  while [ $# -gt 0 ]; do case "$1" in olist-tf-*) shift; exec "$@" ;; esac; shift; done
  exit 1 ;;
*) exit 1 ;;
esac""",
    "gh": "echo fake",
    "az": "exit 0",
    "python3": f'exec "{Path(sys.executable).as_posix()}" "$@"',
    "terraform": """case " $* " in
*" show "*) [ -z "$SHOW_FAIL" ] || exit 1; cat "$SHOW_JSON" ;;
*" apply "*) echo applied >>"$APPLY_LOG" ;;
esac""",
}


def plan(kind, actions):
    change = {"address": f"{kind}.x", "type": kind, "change": {"actions": actions}}
    return json.dumps({"resource_changes": [change]})


SAFE = plan("azurerm_log_analytics_workspace", ["no-op"])
BLOCK = plan("azurerm_storage_account", ["delete", "create"])

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    for name, body in FAKES.items():
        (bin_dir / name).write_text(f"#!/usr/bin/env bash\n{body}\n", newline="\n")
        (bin_dir / name).chmod(0o755)

    def apply(show_json, *, sha=None, show_fail=False):
        """Run apply on a fresh plan file. Returns (exit code, stderr, reached terraform apply)."""
        file, show, log = tmp / "bootstrap.tfplan", tmp / "show.json", tmp / "apply.log"
        file.write_bytes(b"plan bytes")
        show.write_text(show_json)
        log.unlink(missing_ok=True)
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "SHOW_JSON": show.as_posix(),
            "SHOW_FAIL": "1" if show_fail else "",
            "APPLY_LOG": log.as_posix(),
        }
        sha = sha or sha256(file.read_bytes()).hexdigest()
        cmd = [BASH, str(HERE / "tf-toolbox.sh"), "apply", "bootstrap", file.as_posix(), sha]
        out = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return out.returncode, out.stderr, log.exists()

    rc, err, applied = apply(SAFE)
    assert rc == 0 and applied, f"SAFE plan with matching sha must apply: {rc} {err}"
    for name, kwargs in [
        ("BLOCK plan", {"show_json": BLOCK}),
        ("failed terraform show", {"show_json": SAFE, "show_fail": True}),
        ("empty terraform show", {"show_json": ""}),
        ("crashed risk checker", {"show_json": "not json"}),
        ("sha256 mismatch", {"show_json": SAFE, "sha": "b" * 64}),
    ]:
        rc, err, applied = apply(**kwargs)
        assert not applied, f"{name}: reached terraform apply"
        assert rc != 0 and "tf-toolbox:" in err, f"{name}: must refuse with a message: {rc} {err}"

print("tf-toolbox: all checks passed")
