// PROTOTYPE (AIE-50). Throwaway: the floating bottom bar that flips ?variant=. Never ships (PROD gate below).
import { useEffect, useState } from "react";

export type Variant = { key: string; name: string; description: string };

/** The variant key from ?variant=, reload-stable; the setter rewrites the URL without a navigation. */
export function useVariant(variants: Variant[]): [Variant, (key: string) => void] {
  const [key, setKey] = useState(() => new URLSearchParams(location.search).get("variant") ?? variants[0].key);
  const current = variants.find((v) => v.key === key) ?? variants[0];
  useEffect(() => {
    const url = new URL(location.href);
    url.searchParams.set("variant", current.key);
    history.replaceState(null, "", url);
  }, [current.key]);
  return [current, setKey];
}

export function PrototypeSwitcher({
  variants,
  current,
  onChange,
}: {
  variants: Variant[];
  current: Variant;
  onChange: (key: string) => void;
}) {
  const i = variants.indexOf(current);
  const go = (d: number) => onChange(variants[(i + d + variants.length) % variants.length].key);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === "ArrowRight") go(1);
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  });

  if (import.meta.env.PROD) return null;
  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full bg-surface-950 px-4 py-2 text-sm text-surface-50 shadow-xl dark:bg-surface-50 dark:text-surface-950">
      <button className="px-1 font-bold" title="Previous variant (←)" onClick={() => go(-1)}>
        ←
      </button>
      <span>
        <b>{current.key}</b> · {current.name}
        <span className="opacity-70"> — {current.description}</span>
      </span>
      <button className="px-1 font-bold" title="Next variant (→)" onClick={() => go(1)}>
        →
      </button>
    </div>
  );
}
