import { useEffect, useState } from "react";

/**
 * GETs url as JSON, again whenever it changes; null fetches nothing. Until the new response
 * comes, data and error still answer the previous url and loading is true. A late response
 * for an earlier url is dropped, so rapid clock steps are safe.
 */
export function useJson<T>(url: string | null): { data: T | null; error: string | null; loading: boolean } {
  const [got, setGot] = useState<{ url: string; data: T | null; error: string | null } | null>(null);

  useEffect(() => {
    if (url === null) return;
    let current = true;
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then((data: T) => {
        if (current) setGot({ url, data, error: null });
      })
      .catch((e: Error) => {
        if (current) setGot({ url, data: null, error: e.message });
      });
    return () => {
      current = false;
    };
  }, [url]);

  return { data: got?.data ?? null, error: got?.error ?? null, loading: got?.url !== url };
}
