# olist_agent

## Checks

Before reporting work done, run `scripts/check.sh` (or a section: `app`, `web`, `iac`, `image`). CI runs the same script.

The web tests, and how to update the screenshot baselines a restyle changes: `docs/agents/web-tests.md`.

## Agent skills

### Issue tracker

Issues live in Linear (team AIE, project `olist_agent`), accessed via the Linear MCP tools. See `docs/agents/issue-tracker.md`.

Every PR names its Linear issue: branch from the issue's `gitBranchName`. End the PR body with `Fixes AIE-n` once every acceptance criterion on the issue is checked against the work and ticked; otherwise `Part of AIE-n`. See **Linking work to issues** in `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### GitHub reads

Read GitHub through the GitHub connector's MCP tools, not `gh`: PRs and their check runs, diffs, comments and reviews, commits, file contents, issues. Keep `gh` for what the connector lacks: downloading a run's artifacts (the baseline flow in `docs/agents/web-tests.md`), reading a run's log (the deployed URL in `docs/agents/pr-evidence.md`), and listing workflow runs by branch.

### PR screenshots

Before/after screenshots for a PR: capture, store and embed them as `docs/agents/pr-evidence.md` says.
