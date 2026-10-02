import { NotFoundText } from "@/components/common/states";
import { isNotFound, type MaybeFound } from "@/lib/types";
import { Chips } from "./CitationChip";

/** Renders a cited value with chips, or "not found in file". Never a blank, never a guess. */
export function Cited<T>({ value, render }: { value: MaybeFound<T> | null | undefined; render?: (v: T) => React.ReactNode }) {
  if (value == null || isNotFound(value)) return <NotFoundText />;
  return <span>{render ? render(value.value) : String(value.value)}<Chips citations={value.citations} /></span>;
}
