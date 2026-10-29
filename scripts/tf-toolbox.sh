#!/usr/bin/env bash
# The terraform-operator subagent's only way to touch Azure (docs/adr/0007).
# Runs Terraform and az inside this checkout's olist-tf-* container (tools/tf-toolbox), which
# only has IPv4. The repo is mounted at /w, so bootstrap state stays on the host.
#
#   up                               build the image if needed, start the container
#   login                            start a device-code sign-in, print the code, return
#   whoami                           the signed-in account, or exit 1
#   check <root> [--offline]         static checks, plus drift when signed in (never with --offline)
#   plan <root>                      plan -out, risk table, plan file and sha256
#   apply bootstrap <file> <sha256>  apply exactly that plan; bootstrap only
#   down                             az logout and remove the container (plans go with it)
#
# <root> is "bootstrap" or "infra". Run from Git Bash or any POSIX shell with docker and gh.
set -euo pipefail
export MSYS_NO_PATHCONV=1 # stop Git Bash rewriting /w into C:/Program Files/Git/w
cd "$(dirname "$0")/.."

# One container per checkout. A shared name let `up` reuse another worktree's container,
# so checks ran against that worktree's files.
NAME="olist-tf-$(pwd | sha1sum | cut -c1-8)"
# Tagged by content, so editing the Dockerfile rebuilds the image.
IMAGE="olist-tf-toolbox:$(cat tools/tf-toolbox/Dockerfile tools/tf-toolbox/install.py | sha1sum | cut -c1-12)"
# Looked up on demand, so `check --offline` needs neither gh nor a GitHub login (CI).
repo() { gh repo view --json nameWithOwner -q .nameWithOwner; }

die() {
  echo "tf-toolbox: $*" >&2
  exit 1
}
ghvar() { gh variable get "$1" -R "$(repo)"; }

dir_of() {
  case "$1" in
  bootstrap) echo infra/bootstrap ;;
  infra) echo infra ;;
  *) die "root must be bootstrap or infra, got '$1'" ;;
  esac
}

# Run a command in the container. ENVS holds per-root -e flags.
ENVS=()
x() { docker exec "${ENVS[@]}" -w /w "$NAME" "$@"; }

running() { [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" = true ]; }
need_up() { running || die "container not running: run '$0 up' first"; }
need_login() {
  need_up
  x az account set --subscription "$(ghvar AZURE_SUBSCRIPTION_ID)" 2>/dev/null ||
    die "not signed in: run '$0 login' and complete the device-code sign-in"
}

# Variables each root needs for a real plan. Values come from the repo's GitHub
# variables, so nothing is hard-coded and nothing secret is stored here.
live_env() {
  ENVS=(-e "TF_DATA_DIR=/tmp/tfdata/$1" -e "ARM_SUBSCRIPTION_ID=$(ghvar AZURE_SUBSCRIPTION_ID)")
  if [ "$1" = bootstrap ]; then
    local r
    r=$(repo)
    ENVS+=(-e "TF_VAR_github_repository=$r")
    ENVS+=(-e "TF_VAR_github_sub_prefix=$(gh api "repos/$r/actions/oidc/customization/sub" --jq .sub_claim_prefix)")
  else
    # GitHub secrets, so they can't be read back; pass them from your shell.
    : "${TF_VAR_budget_alert_email:?export TF_VAR_budget_alert_email=<the BUDGET_ALERT_EMAIL secret> to plan infra}"
    : "${TF_VAR_operator_object_id:?export TF_VAR_operator_object_id=<the AZURE_OPERATOR_OBJECT_ID secret> to plan infra}"
    ENVS+=(-e "TF_VAR_budget_alert_email=$TF_VAR_budget_alert_email")
    ENVS+=(-e "TF_VAR_operator_object_id=$TF_VAR_operator_object_id")
  fi
}

live_init() {
  local dir
  dir=$(dir_of "$1")
  # Both roots keep state in the tfstate storage account. The exception is bootstrap's
  # very first apply, before that account exists: a gitignored local_override.tf forces
  # local state, and a local backend takes no storage_account_name (README).
  if [ "$1" = bootstrap ] && [ -f "$dir/local_override.tf" ]; then
    x terraform -chdir="$dir" init -input=false -no-color >/dev/null
  else
    x terraform -chdir="$dir" init -input=false -no-color \
      -backend-config="storage_account_name=$(ghvar TFSTATE_STORAGE_ACCOUNT)" >/dev/null
  fi
}

FAILED=0
step() {
  local name=$1 out
  shift
  if out=$("$@" 2>&1); then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    echo "$out" | tail -40 | sed 's/^/      /'
    FAILED=1
  fi
}

cmd_up() {
  docker image inspect "$IMAGE" >/dev/null 2>&1 || docker build -q -t "$IMAGE" tools/tf-toolbox >/dev/null
  if ! running; then
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" -v "$(pwd -W 2>/dev/null || pwd):/w" "$IMAGE" sleep infinity >/dev/null
  fi
  echo "UP $NAME ($IMAGE)"
}

cmd_login() {
  need_up
  docker exec -d "$NAME" sh -c \
    "az login --use-device-code --tenant $(ghvar AZURE_TENANT_ID) --output none >/tmp/login.log 2>&1"
  local code=""
  for _ in $(seq 30); do
    code=$(docker exec "$NAME" sh -c 'grep -o "code [A-Z0-9]*" /tmp/login.log 2>/dev/null' || true)
    [ -n "$code" ] && break
    sleep 1
  done
  [ -n "$code" ] || die "no device code after 30s: $(docker exec "$NAME" cat /tmp/login.log 2>&1)"
  echo "LOGIN https://login.microsoft.com/device ${code#code }"
}

cmd_whoami() {
  need_login
  x az account show --query "{user:user.name, subscription:name}" -o tsv
}

cmd_check() {
  local root=$1 offline=$2 dir
  dir=$(dir_of "$root")
  [ -z "$offline" ] || [ "$offline" = --offline ] || die "check takes only --offline after the root, got '$offline'"
  need_up
  # Static checks need no Azure access. They use their own data dir because
  # -backend=false and a real backend can't share one. GITHUB_TOKEN, when set (CI),
  # spares tflint --init the anonymous rate limit on the azurerm ruleset download.
  ENVS=(-e "TF_DATA_DIR=/tmp/tfdata/$root-static" -e GITHUB_TOKEN)
  step "fmt" x terraform -chdir="$dir" fmt -check -recursive
  step "init (no backend)" x terraform -chdir="$dir" init -backend=false -input=false -no-color
  step "validate" x terraform -chdir="$dir" validate -no-color
  step "tflint" x sh -c "tflint --init --config /w/infra/.tflint.hcl >/dev/null && tflint --chdir $dir --config /w/infra/.tflint.hcl"
  step "test (mock providers)" x terraform -chdir="$dir" test -no-color
  if [ "$offline" = --offline ]; then
    echo "SKIP  drift (--offline)"
  elif x az account show >/dev/null 2>&1; then
    need_login
    live_env "$root"
    live_init "$root"
    # Drift: state and Azure disagree because something changed Azure outside Terraform, or an
    # apply half-landed. Read resource_drift from the plan JSON: -detailed-exitcode exits 2 on
    # any refresh, even when nothing drifted.
    local out rc=0
    if out=$(x sh -c "terraform -chdir=$dir plan -refresh-only -lock=false -input=false -no-color -out=/tmp/refresh.tfplan >/dev/null &&
        terraform -chdir=$dir show -json /tmp/refresh.tfplan > /tmp/refresh.json" 2>&1); then
      out=$(x python3 scripts/tf_risk.py /tmp/refresh.json --drift) || rc=$?
      if [ $rc -eq 0 ]; then
        echo "PASS  drift (none)"
      else
        echo "FAIL  drift detected"
        printf '%s\n' "$out" | sed 's/^/      /'
        FAILED=1
      fi
      x rm -f /tmp/refresh.tfplan /tmp/refresh.json
    else
      echo "FAIL  drift check errored"
      echo "$out" | tail -20 | sed 's/^/      /'
      FAILED=1
    fi
  else
    echo "SKIP  drift (not signed in)"
  fi
  return $FAILED
}

cmd_plan() {
  local root=$1 dir out rc=0 sha lock=()
  dir=$(dir_of "$root")
  need_login
  live_env "$root"
  live_init "$root"
  # infra/ is never applied from here, so never take its state lock: CD might need it.
  [ "$root" = infra ] && lock=(-lock=false)
  x mkdir -p /tmp/plans
  out=$(x terraform -chdir="$dir" plan -input=false -no-color "${lock[@]}" -out="/tmp/plans/$root.tfplan" 2>&1) ||
    {
      echo "$out" | tail -40
      die "plan failed"
    }
  echo "$out" | grep -E '^(Plan:|No changes\.)' || true
  x sh -c "terraform -chdir=$dir show -json /tmp/plans/$root.tfplan > /tmp/plans/$root.json"
  x python3 scripts/tf_risk.py "/tmp/plans/$root.json" --root "$root" || rc=$?
  sha=$(x sha256sum "/tmp/plans/$root.tfplan" | cut -d' ' -f1)
  echo
  echo "PLAN_FILE=/tmp/plans/$root.tfplan"
  echo "PLAN_SHA256=$sha"
  return $rc
}

cmd_apply() {
  local root=$1 file=$2 sha=$3 actual
  [ "$root" = bootstrap ] || die "apply is bootstrap-only; infra/ is applied by CD on merge to main"
  need_login
  live_env bootstrap
  actual=$(x sha256sum "$file" | cut -d' ' -f1) || die "no plan file at $file"
  [ "$actual" = "$sha" ] || die "plan file changed since it was approved ($actual != $sha)"
  # Re-check rather than trust the earlier report. The gate exits 0 only when apply may
  # proceed; BLOCK, a broken `terraform show` or a crashed checker all refuse.
  x sh -c "terraform -chdir=infra/bootstrap show -json $file | python3 scripts/tf_risk.py - --root bootstrap --gate" >/dev/null ||
    die "risk gate refused: BLOCK, or the check itself failed. Change the code, don't apply this plan"
  x terraform -chdir=infra/bootstrap apply -input=false -no-color "$file"
  x rm -f "$file"
}

cmd_down() {
  if running; then
    docker exec "$NAME" az logout >/dev/null 2>&1 || true
  fi
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  echo "DOWN $NAME removed"
}

case "${1:-}" in
up) cmd_up ;;
login) cmd_login ;;
whoami) cmd_whoami ;;
check) cmd_check "${2:?root}" "${3:-}" ;;
plan) cmd_plan "${2:?root}" ;;
apply) cmd_apply "${2:?root}" "${3:?plan file}" "${4:?sha256}" ;;
down) cmd_down ;;
*) die "usage: $0 up|login|whoami|check <root> [--offline]|plan <root>|apply bootstrap <file> <sha256>|down" ;;
esac
