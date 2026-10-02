import { API_URL, ApiError } from "./api";

export type SSEEvent = { event: string; data: unknown };

/** Incremental text/event-stream parser: push() raw chunks, get whole events. */
export function createSSEParser(onEvent: (e: SSEEvent) => void) {
  let buf = "";
  return {
    push(chunk: string) {
      buf += chunk.replace(/\r\n/g, "\n");
      let i: number;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const frame = buf.slice(0, i);
        buf = buf.slice(i + 2);
        let event = "message";
        const data: string[] = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (!data.length) continue;
        const raw = data.join("\n");
        let parsed: unknown = raw;
        try { parsed = JSON.parse(raw); } catch { /* plain text payload */ }
        onEvent({ event, data: parsed });
      }
    },
  };
}

export async function postSSE(path: string, body: unknown, onEvent: (e: SSEEvent) => void, signal?: AbortSignal) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, `Stream failed (${res.status})`);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const parser = createSSEParser(onEvent);
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    parser.push(value);
  }
}
