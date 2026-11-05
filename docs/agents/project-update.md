# Project update at milestone close

Every milestone ends with a **project update** on the olist_agent Linear project, after its lesson document. Josh asks for it; the agent drafts it, Josh approves it, the agent posts it.

## When

The moment the last open issue in a milestone closes (the milestone's progress reaches 100%; usually the spec, closed after the milestone-close ticket), ask Josh in one line whether to write the update now. Write it only on his yes.

## Sources

The milestone's issues are those whose `projectMilestone` is the milestone: `list_issues` on the project with `fields: ["id", "title", "status", "projectMilestone"]`, plus `parentId: "<spec>"` for the spec's children.

| Section | Read |
|---|---|
| **Completed** | Each Done issue's title and its PR (`attachments`); the spec's closing comment (the "done when" check and any departures from the spec); the deploy check. |
| **Lessons** | The milestone's lesson document, linked from the milestone description. Summarise its sections in a few bullets and link it; never restate it. |
| **Roadblocks** | Issues created during the milestone outside it: follow-ups (`relatedTo` a milestone issue) and `retro` issues (`label: "retro"`, `createdAt` after the milestone started). Closing comments that record a decision or a miss. The lesson's process lessons. For each roadblock: what blocked, how it was resolved, and the issue or PR that resolved it. |

## Write

Run `/product-management:stakeholder-update`. Answer its two questions without asking Josh: the type is **ad-hoc, milestone close**, and the audience is the **engineering team**. Use its engineering template, reshaped into these sections:

1. **Status** line: the milestone, its close date, the health (on track unless an open follow-up puts the next milestone at risk).
2. **Completed**: shipped work grouped by outcome, each with its issue and PR.
3. **Lessons**: the lesson document's points, with the link.
4. **Roadblocks**: each one Resolved in the skill's ROAM sense (what blocked, how it was resolved, the link). A roadblock still open is Owned, with its issue.
5. **Next**: the next milestone and the open follow-ups it inherits.

Show the draft to Josh before posting.

## Post

After Josh approves: `save_status_update` with `type: "project"`, `project: "olist_agent"`, the approved markdown as `body`, and `health` (`onTrack`, `atRisk` or `offTrack`). Link the posted update from the milestone description, beside the lesson.
