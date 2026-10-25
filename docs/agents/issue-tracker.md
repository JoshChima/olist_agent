# Issue tracker: Linear

Issues and specs for this repo live in Linear: team **AI Enabled Engineer** (key `AIE`), project **olist_agent** (`P-AIE-3`, https://linear.app/gloph-software-factory/project/olist-agent-dc2eb913c358). Use whichever Linear MCP server is connected: the claude.ai Linear connector, or the productivity plugin's `linear` server. Both reach the same workspace, and the tool names below (`save_issue`, `get_issue`, ...) are the same in each.

Linear is the only task list here. Don't create `TASKS.md` or a `memory/` folder in the repo (the productivity plugin's task- and memory-management skills); open work goes in Linear, and session context goes in Claude's own memory.

## Conventions

- **Create an issue**: `save_issue` with `team: "AIE"`, `project: "olist_agent"`, `title`, and a markdown `description`. New issues start in `Backlog`.
- **Read an issue**: `get_issue` with the identifier (e.g. `AIE-12`); `list_comments` for the thread.
- **List issues**: `list_issues` with `team: "AIE"`, `project: "olist_agent"`, plus `label` / `state` filters.
- **Make an issue a sub-issue of a parent**: `save_issue` with `parentId: "AIE-<n>"`.
- **Comment on an issue**: `save_comment` on the issue.
- **Apply / remove labels**: `save_issue` with `id` and `addLabels` / `removeLabels`.
- **Close**: first check **every acceptance criterion** against the delivered work: run the test, hit the endpoint, read the config. Tick the met ones in the description. Move any unmet one to a follow-up issue linked with `relatedTo`, and say so in the closing comment. Then comment, and `save_issue` with `state: "Done"` (completed) or `state: "Canceled"` (won't do). Duplicates: `duplicateOf: "AIE-<n>"`.

Statuses in AIE: Backlog, Todo, In Progress, Done, Canceled, Duplicate.

## Linking work to issues

The Linear GitHub integration is installed on `JoshChima/olist_agent`. It links PRs to issues and moves them through statuses on its own, but only when the PR names the issue. Every change to the repo goes through a PR that names one.

- **Issue first.** Before opening a PR, find its issue, or create one if none exists. As a last resort, `AIE-NEW` in the PR description makes Linear create and link one.
- **Branch name.** Use the issue's `gitBranchName`, which `save_issue` and `get_issue` return (e.g. `joshchima/aie-15-link-every-pr-...`). The issue ID in the branch links the PR as soon as it opens.
- **PR body.** End it with a magic-word line. Linear reads the title and description, not comments.

  | Line | Use when | Effect |
  |---|---|---|
  | `Fixes AIE-n` | this PR finishes the issue | In Progress when opened, **Done when merged** |
  | `Part of AIE-n` | more PRs for this issue will follow | In Progress, stays open when merged |
  | `Related to AIE-n` | it touches the issue without advancing it | link only, no status change |

  One PR can fix several issues: `Fixes AIE-3, AIE-4`. When an issue takes several PRs, use `Part of` on every one except the last, which uses `Fixes`. Otherwise the first merge closes the issue early.

  `Fixes` closes the issue at merge with nobody checking, so it's where the **Close** criteria check happens: write `Fixes` only when every acceptance criterion is met, and otherwise use `Part of` plus a follow-up issue.
- **Build tickets with `/implement AIE-n`.** Its `/code-review` checks the diff against the ticket's spec, which catches a missed acceptance criterion before the PR exists.
- **Done means deployed.** Merging to `main` triggers CD, so merged → Done matches "shipped".
- **No PR?** Close a non-code issue (e.g. a manual verification) by hand, as in **Close** above, with a comment giving the evidence.

## When a skill says "publish to the issue tracker"

Create a Linear issue in team AIE, project olist_agent.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above. The user will normally pass an `AIE-<n>` identifier or a Linear URL.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** sub-issues as tickets.

- **Map**: an issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body.
- **Child ticket**: a sub-issue of the map (`parentId`), labelled `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Create the `wayfinder:*` labels in team AIE on first use.
- **Blocking**: Linear's native relation, `save_issue` with `blockedBy: ["AIE-<n>", ...]` on the child. A ticket is unblocked when every blocker is Done or Canceled.
- **Frontier**: list the map's open sub-issues, drop any with an open blocker or an assignee; first in map order wins.
- **Claim**: `save_issue` with `assignee: "me"` and `state: "In Progress"`, the session's first write.
- **Resolve**: comment the answer, set `state: "Done"`, then append a context pointer (gist + link) to the map's Decisions-so-far.
