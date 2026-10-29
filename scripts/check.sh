#!/usr/bin/env bash
# Every CI check that needs no Azure. ci.yml's jobs call their section, so a local
# pass means the same commands pass in CI.
#
#   scripts/check.sh                  all sections
#   scripts/check.sh app|web|iac|image ...
#
# Needs uv, node (for corepack) and Docker. Terraform and tflint run in the tf-toolbox
# container, shellcheck and trivy in their own images. Stops at the first failure.
set -euo pipefail
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
cd "$(dirname "$0")/.."
HOST=$(pwd -W 2>/dev/null || pwd)

# Git Bash would rewrite container paths like /w into Windows paths. Scoped to docker
# because the same setting breaks the corepack shim on Windows.
dk() { MSYS_NO_PATHCONV=1 docker "$@"; }

# A named volume keeps trivy's vulnerability DB between local runs.
trivy() {
  dk run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache \
    -v "$HOST:/w" -w /w aquasec/trivy:0.76.1 "$@"
}

app() {
  (
    cd app
    uv sync --locked
    uv run ruff check .
    uv run ruff format --check .
    uv run pyright
    uv run pytest
    # Repo scripts and the toolbox installer: same ruff config, pyright in standard mode
    # (../pyrightconfig.json), since they walk untyped `terraform show -json` output.
    uv run ruff check ../scripts ../tools
    uv run ruff format --check ../scripts ../tools
    uv run pyright -p ..
  )
}

web() {
  (
    cd app/web
    corepack pnpm install --frozen-lockfile
    corepack pnpm build # includes tsc type-check
  )
}

iac() {
  # fmt, validate, tflint and terraform test (mock providers), never touching Azure.
  scripts/tf-toolbox.sh up
  scripts/tf-toolbox.sh check bootstrap --offline
  scripts/tf-toolbox.sh check infra --offline
  # The gates between agents and real Azure (ADR-0007): risk tiers, the apply gate,
  # the subagent's Bash guard, the apply approval hook and tf-toolbox.sh apply itself.
  python3 scripts/test_tf_risk.py
  python3 scripts/test_guards.py
  python3 scripts/test_tf_toolbox.py
  dk run --rm -v "$HOST:/mnt" -w /mnt koalaman/shellcheck:v0.10.0 scripts/*.sh
  # vars.* are never masked, so anything read from them lands in the public logs.
  if grep -rnE '\{\{ *vars\.' .github/workflows; then
    echo "workflows must read Azure IDs from secrets, not vars" >&2
    exit 1
  fi
  trivy config --quiet --severity HIGH,CRITICAL --exit-code 1 \
    --skip-dirs app/.venv --skip-dirs app/web/node_modules .
}

image() {
  docker build -q -t olist-agent:ci app >/dev/null
  # Fail only on findings that have a fix to take. Detailed mode prints findings, not
  # a row for every package.
  trivy image --quiet --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
    --table-mode detailed olist-agent:ci
}

[ $# -gt 0 ] || set -- app web iac image
for s in "$@"; do
  case "$s" in
  app | web | iac | image) ;;
  *)
    echo "check.sh: unknown section '$s' (app, web, iac, image)" >&2
    exit 2
    ;;
  esac
  echo "== $s"
  "$s"
done
echo "check.sh: all passed"
