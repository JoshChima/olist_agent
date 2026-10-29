# 7. A terraform-operator subagent, gated by scripts rather than prompts

Date: 2026-10-24 · Status: Accepted

## Context
In P0, a bootstrap apply landed only partway. The two federated credentials were updated in separate requests, and the `plan` one failed when the network reset the connection. The state file recorded the new subject anyway, so CI's PR plans failed while state and Azure disagreed. Two problems made this worse:
- **IPv6 resets.** The developer's network resets IPv6 connections to Azure. Docker containers only use IPv4, which is why running Terraform in a container fixed it.
- **Bootstrap has no pipeline.** Its state is local by design (ADR-0005), so a person or agent has to apply it.

HashiCorp's `terraform` Claude Code plugin was evaluated first. It wraps the Terraform MCP server and nothing else:
- registry and documentation lookups;
- HCP Terraform workspaces and runs.

It has no skills or agents. Its container can't see the repo, and it never runs the CLI. Its run tools only target HCP Terraform, which this repo doesn't use.

## Decision
- **A project subagent does the work.** `.claude/agents/terraform-operator.md` (Sonnet) runs all Terraform and `az` work against real Azure, through `scripts/tf-toolbox.sh` only. The script drives the `olist-tf` container (`tools/tf-toolbox/`), which runs Terraform 1.16.6, Azure CLI 2.90.0 and tflint 0.64.0, the same versions as CI.
- **Checks use Terraform's own tooling:**
  - `fmt`, `validate` and tflint;
  - `terraform test` with mock providers: contract tests in `infra/**/tests/` that pin ADR decisions;
  - `plan -refresh-only -detailed-exitcode` for drift;
  - `plan -out` plus `show -json`, passed to `scripts/tf_risk.py`.
- **`tf_risk.py` decides the risk tier from Terraform's own fields** (`actions`, `action_reason`, `replace_paths`):

  | Tier | Meaning |
  |---|---|
  | SAFE | Nothing to watch |
  | REVIEW | Changes to identity or auth, or anything in bootstrap |
  | DANGER | Any delete or replace |
  | BLOCK | Delete or replace of a protected stateful resource |

  CI's `plan` job runs the same script: it adds the table to the PR comment and fails the job on BLOCK.
- **The gates are enforced, not requested:**
  - The subagent can't talk to the user. It returns NEEDS: LOGIN, APPROVAL or CODE_CHANGE, and the main agent relays it.
  - The script applies only `bootstrap`, only the exact plan file whose sha256 was approved, and never a BLOCK plan.
  - `.claude/settings.json` has an `ask` rule on `scripts/tf-toolbox.sh apply`, plus a project `PreToolUse` hook (`scripts/ask_tf_apply.py`) that returns `permissionDecision: "ask"` for any `tf-toolbox.sh apply`. A person approves every apply command line.
  - A frontmatter `PreToolUse` hook (`scripts/guard_tf_bash.py`) limits the subagent's Bash to that one script.
  - For a plain-language account of why the hash exists, see [Why apply needs the plan's sha256](../../README.md#why-apply-needs-the-plans-sha256).
- **Sign-in happens once per task.** It's a device-code `az login` in the container; `down` logs out and removes the container.
- **Only the plugin's read-only registry tools are used**, for checking azurerm `~> 5.10` arguments.

## Consequences
- `infra/` is still applied only by CD. The subagent plans and checks it, which catches failures before a PR is pushed.
- The user still approves twice: once on the report, once on the permission prompt. That's deliberate: an agent that computed a hash can't approve its own plan.
- The frontmatter hook only runs in a trusted workspace, so it's defense in depth. The approval gate is the settings `ask` rule plus the project hook.
- **Live test, 2026-10-24.** The `ask` rule alone did *not* prompt. That session was in auto mode, and the rule had been added mid-session. That's why the hook exists. Both only take effect in a session started after they're added. Until a fresh session confirms the prompt, treat the script's own checks (bootstrap only, exact hash, fail-closed risk check) as the guarantee. If a prompt still doesn't appear, make `apply` require a typed confirmation from a real terminal.
- **Drift needs the JSON.** `plan -refresh-only -detailed-exitcode` exits 2 on any refresh, even with no drift, so drift is read from the plan's `resource_drift`.
- **The apply risk check fails closed.** Only checker exit 0 (SAFE/REVIEW) or 2 (DANGER) can proceed. A broken `terraform show` was found to slip past a refuse-only-on-3 check.
- New stateful resource types (Postgres in P1, Key Vault in P2) must be added to `PROTECTED` in `tf_risk.py` in the same PR that introduces them.
