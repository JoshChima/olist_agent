// The design system's semantic tokens as Skeleton classes (ADR-0011; the artifact linked on AIE-47).
// Concord's dark root is surface-900, so the card and its hairline sit one step off it: those two are
// not mirrored pairings, hence `dark:`, which is Tailwind's media variant and so follows the OS.

/** `card`: tiles, panels, the app bar and the rail. */
export const CARD = "bg-surface-50 dark:bg-surface-800";
/** `line`: every hairline. */
export const LINE = "border-surface-200 dark:border-surface-700";
/** `ink-muted`: labels, captions, "Loading…". */
export const MUTED = "text-surface-600 dark:text-surface-200";
/** `small`: 13px/18px. */
export const SMALL = "text-[13px] leading-[18px]";
/** `focus`: a solid 2px ring, 2px offset, on every control. */
export const FOCUS =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 dark:focus-visible:outline-primary-300";
/** A one-line `role="status"` strip on the `info-tonal` ground: the delta strip, "No data loaded yet.". */
export const STATUS = `preset-tonal-tertiary rounded-base truncate px-3 py-2 tabular-nums ${SMALL}`;
