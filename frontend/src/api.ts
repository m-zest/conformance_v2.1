import { useCallback, useEffect, useRef, useState } from "react";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T = any>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const response = await fetch("/api" + path, {
    method: options.method ?? (options.body === undefined ? "GET" : "POST"),
    headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "same-origin",
  });
  if (!response.ok) {
    let message = "Request failed (" + response.status + ")";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg;
    } catch {
      /* keep the generic message */
    }
    if (response.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("conformance:signed-out"));
    throw new ApiError(response.status, message);
  }
  return response.json();
}

/** Fetches a resource and keeps the previous result on screen while a refresh is in flight. */
export function useApi<T = any>(path: string | null, pollMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const current = useRef(path);
  current.current = path;

  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try {
      const result = await api<T>(path);
      if (current.current === path) {
        setData(result);
        setError(null);
      }
    } catch (e) {
      if (current.current === path) setError((e as Error).message);
    } finally {
      if (current.current === path) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (!path) {
      setData(null);
      return;
    }
    load();
    if (!pollMs) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, pollMs);
    return () => window.clearInterval(timer);
  }, [path, pollMs, load]);

  return { data, error, loading, reload: load };
}

export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "" && value !== false) search.set(key, String(value));
  }
  const text = search.toString();
  return text ? "?" + text : "";
}
