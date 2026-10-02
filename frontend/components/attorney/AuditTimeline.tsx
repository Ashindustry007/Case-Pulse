import { fmtDateTime } from "@/lib/format";
import type { ShareAudit } from "@/lib/types";

const LABEL: Record<string, string> = {
  released: "released", viewed: "viewed", document_opened: "opened", request_completed: "marked sent",
  request_dismissed: "dismissed request", revoked: "revoked", invite_sent: "invite sent", invite_accepted: "invite accepted",
};

export function AuditTimeline({ audit }: { audit: ShareAudit }) {
  const diff = new Map(audit.versions.map((v) => [v.policy.version, v]));
  return (
    <ol className="space-y-3 border-l pl-4 text-[13px]">
      {[...audit.events].reverse().map((e) => {
        const v = e.event === "released" && e.policy_version != null ? diff.get(e.policy_version) : undefined;
        return (
          <li key={e.id} className="relative before:absolute before:-left-[21px] before:top-1.5 before:size-1.5 before:rounded-full before:bg-primary/70">
            <span className="text-xs text-muted-foreground">{fmtDateTime(e.at)}</span><br />
            {e.event === "released" ? <b>v{e.policy_version} released</b> : LABEL[e.event] ?? e.event}
            {e.actor_email && <span className="text-muted-foreground"> · {e.actor_email}</span>}
            {typeof e.meta?.document_id === "string" && <span> · {String(e.meta.document_id)}</span>}
            {v && (v.added.length > 0 || v.removed.length > 0) && (
              <span className="text-muted-foreground"> ({v.added.map((a) => `+${a}`).concat(v.removed.map((r) => `−${r}`)).join(" ")})</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
