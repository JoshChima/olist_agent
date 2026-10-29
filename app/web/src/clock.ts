import { useEffect, useState } from "react";

// The dataset's first and last days (GLOSSARY.md "Clock"). ISO dates compare as strings.
export const FIRST_DAY = "2016-09-04";
export const LAST_DAY = "2018-10-17";
const DEFAULT_DAY = "2017-01-01"; // past the sparse 2016 data
const KEY = "clock";

const clamp = (d: string) => (d < FIRST_DAY ? FIRST_DAY : d > LAST_DAY ? LAST_DAY : d);
const isDay = (s: string | null): s is string => !!s && /^\d{4}-\d{2}-\d{2}$/.test(s);

function stored(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null; // storage blocked: the URL still carries the clock
  }
}

/** The clock lives in the URL as ?clock=YYYY-MM-DD, mirrored to localStorage (ADR-0009). */
export function useClock(): [string, (day: string) => void] {
  const [clock, setClock] = useState(() => {
    const fromUrl = new URLSearchParams(location.search).get("clock");
    return clamp([fromUrl, stored()].find(isDay) ?? DEFAULT_DAY);
  });
  useEffect(() => {
    const url = new URL(location.href);
    url.searchParams.set("clock", clock);
    history.replaceState(null, "", url);
    try {
      localStorage.setItem(KEY, clock);
    } catch {
      // see stored()
    }
  }, [clock]);
  return [clock, (day) => isDay(day) && setClock(clamp(day))];
}

export type Step = "day" | "week" | "month";

/** The day n steps from day. A month step keeps the day of month where it can (Jan 31 + 1 month = Feb 28). */
export function step(day: string, unit: Step, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  if (unit === "month") {
    const dom = d.getUTCDate();
    d.setUTCDate(1);
    d.setUTCMonth(d.getUTCMonth() + n);
    const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(dom, last));
  } else {
    d.setUTCDate(d.getUTCDate() + n * (unit === "week" ? 7 : 1));
  }
  return d.toISOString().slice(0, 10);
}
