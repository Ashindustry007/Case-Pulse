"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";

export function useApi<T>(path: string | null) {
  const [state, setState] = useState<{ data?: T; error?: ApiError; loading: boolean }>({ loading: !!path });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) { setState({ loading: false }); return; }
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true }));
    api<T>(path, { signal: ctrl.signal }).then(
      (data) => setState({ data, loading: false }),
      (error) => { if (!ctrl.signal.aborted) setState({ error, loading: false }); },
    );
    return () => ctrl.abort();
  }, [path, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}
