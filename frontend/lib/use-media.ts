"use client";
import { useEffect, useState } from "react";

/** matchMedia as state. `undefined` until mounted so server and first client render agree. */
export function useMedia(query: string): boolean | undefined {
  const [matches, setMatches] = useState<boolean | undefined>(undefined);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const update = () => setMatches(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [query]);
  return matches;
}
