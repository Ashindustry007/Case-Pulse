import { describe, expect, it } from "vitest";
import { createSSEParser, type SSEEvent } from "./sse";

describe("createSSEParser", () => {
  it("reassembles frames split across chunks", () => {
    const got: SSEEvent[] = [];
    const p = createSSEParser((e) => got.push(e));
    p.push('event: segment\ndata: {"id":"s1","te');
    p.push('xt":"Hello","citations":[]}\n');
    p.push("\nevent: done\ndata: {\"followups\":[]}\n\n");
    expect(got).toEqual([
      { event: "segment", data: { id: "s1", text: "Hello", citations: [] } },
      { event: "done", data: { followups: [] } },
    ]);
  });
  it("passes error events through and tolerates CRLF", () => {
    const got: SSEEvent[] = [];
    const p = createSSEParser((e) => got.push(e));
    p.push('event: error\r\ndata: {"message":"boom"}\r\n\r\n');
    expect(got).toEqual([{ event: "error", data: { message: "boom" } }]);
  });
});
