# Issue tracker: Linear

Issues and specs for this repo live in Linear: team **AI Enabled Engineer** (key `AIE`), project **olist_agent** (`P-AIE-3`, https://linear.app/gloph-software-factory/project/olist-agent-dc2eb913c358). Use the Linear MCP tools (`mcp__claude_ai_Linear__*`) for all operations.

## Conventions

- **Create an issue**: `save_issue` with `team: "AIE"`, `project: "olist_agent"`, `title`, and a markdown `description`. New issues start in `Backlog`.
- **Read an issue**: `get_issue` with the identifier (e.g. `AIE-12`); `list_comments` for the thread.
- **List issues**: `list_issues` with `team: "AIE"`, `project: "olist_agent"`, plus `label` / `state` filters.
- **Make an issue a sub-issue of a parent**: `save_issue` with `parentId: "AIE-<n>"`.
- **Comment on an issue**: `save_comment` on the issue.
- **Apply / remove labels**: `save_issue` with `id` and `addLabels` / `removeLabels`.
- **Close**: comment, then `save_issue` with `state: "Done"` (completed) or `state: "Canceled"` (won't do). Duplicates: `duplicateOf: "AIE-<n>"`.

Statuses in AIE: Backlog, Todo, In Progress, Done, Canceled, Duplicate.

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
