import { uniqueCitations } from "./citations";
import type { AnswerSegment } from "./types";

export function selectionSources(segments: AnswerSegment[], ids: string[]) {
  const chosen = segments.filter((s) => ids.includes(s.id));
  return {
    citations: uniqueCitations(chosen.flatMap((s) => s.citations ?? [])),
    needsVerify: chosen.some((s) => !s.citations?.length),
  };
}

/** DOM side: which [data-seg] spans inside root does the range touch? */
export function segmentIdsInRange(root: HTMLElement, range: Range): string[] {
  return [...root.querySelectorAll<HTMLElement>("[data-seg]")]
    .filter((el) => range.intersectsNode(el))
    .map((el) => el.dataset.seg!)
    .filter(Boolean);
}
