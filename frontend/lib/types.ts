/** Single re-export point for generated API types. If `make types` renames a schema, fix it HERE only. */
import type { components } from "./api-types";

type S = components["schemas"];
export type Citation = S["Citation"];
export type NotFound = S["NotFound"];
export type Cited<T> = { value: T; citations: Citation[] };
export type MaybeFound<T> = Cited<T> | NotFound;
export const isNotFound = (x: unknown): x is NotFound =>
  !!x && typeof x === "object" && (x as NotFound).not_found === true;

export type UserOut = S["UserOut"];
export type Role = UserOut["role"];
export type MatterSummary = S["MatterSummary"];
export type Overview = S["Overview"];
export type Brief = S["Brief"];
export type Changes = S["Changes"];
export type Delta = S["Delta"];
export type VisitResponse = S["VisitResponse"];
export type DeadlineItem = S["DeadlineItem"];
export type Deadlines = S["Deadlines"];
export type Costs = S["Costs"];
export type Providers = S["Providers"];
export type ProviderSummary = S["ProviderSummary"];
export type Timeline = S["Timeline"];
export type SourceRecord = S["SourceRecord"];
export type DocumentPage = S["DocumentPage"];
/** SSE-only model (not in OpenAPI); mirrors backend/app/contracts.py AnswerSegment. */
export type AnswerSegment = { id: string; text: string; citations: Citation[] };
export type LocateResult = S["LocateResult"];
export type SuggestedQuestions = S["SuggestedQuestions"];
export type ProviderDraft = S["ProviderDraft"];
export type DraftFlag = S["DraftFlag"];
export type DigestRun = S["DigestRun"];
export type AiCostReport = S["AiCostReport"];
export type FirmCostReport = S["FirmCostReport"];
export type ProviderCase = S["ProviderCase"];
export type ProviderCaseSummary = S["ProviderCaseSummary"];
export type ProviderRequest = S["ProviderRequest"];
export type ShareCandidates = S["ShareCandidates"];
export type Grant = S["Grant"];
export type ReleaseResult = S["ReleaseResult"];
export type ShareAudit = S["ShareAudit"];
export type ShareEvent = S["ShareEvent"];
export type ShareField = S["ReleaseRequest"]["fields"][number];
