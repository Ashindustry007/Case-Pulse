/** Markdown-lite for AI text: **bold**, "- " / "1." bullets, line breaks. No HTML, no dependencies.
 *  Ask answers arrive as many small segments (split at citation boundaries), so formatting state is carried
 *  across segments: a `**` opened in one segment closes in a later one, and a bullet can start a segment. */
export type Tok =
  | { t: "text"; s: string; b: boolean }
  | { t: "bullet" }
  | { t: "br"; double: boolean };

export type RichState = { bold: boolean; lineStart: boolean; started: boolean; lastWasBreak: boolean };
export const newState = (): RichState => ({ bold: false, lineStart: true, started: false, lastWasBreak: false });

const BULLET = /^\s*(?:[-*•–]|\d+[.)])\s+/;

export function tokenize(text: string, st: RichState = newState()): Tok[] {
  const out: Tok[] = [];
  for (const piece of text.split(/(\*\*|\n)/)) {
    if (piece === "") continue;
    if (piece === "**") { st.bold = !st.bold; continue; }
    if (piece === "\n") {
      if (!st.started) continue;                       // never open with a blank line
      out.push({ t: "br", double: st.lastWasBreak });  // a second consecutive newline = paragraph gap
      st.lastWasBreak = true; st.lineStart = true;
      continue;
    }
    let s = piece;
    if (st.lineStart) {
      const m = BULLET.exec(s);
      if (m) { out.push({ t: "bullet" }); st.started = true; st.lastWasBreak = false; s = s.slice(m[0].length); }
      else s = s.replace(/^\s+/, "");
    }
    if (s.includes("|")) {
      // Markdown table rows → readable lines. Separator rows (|---|---|) vanish; "| a | b |" becomes "a · b".
      if (/^[\s|:-]+$/.test(s) && s.includes("-")) continue;
      const lead = /^\s*\|/.test(s);
      s = s.replace(/^\s*\|\s*/, "").replace(/\s*\|\s*$/, "").replace(/\s*\|\s*/g, " · ");
      if (lead && !st.lineStart && s) s = `· ${s}`;
    }
    if (!s) continue;
    out.push({ t: "text", s, b: st.bold });
    st.lineStart = false; st.started = true; st.lastWasBreak = false;
  }
  return out;
}

/** Plain text with all markup removed (for tooltips, clamping, tests). */
export const plain = (text: string): string =>
  tokenize(text).map((k) => (k.t === "text" ? k.s : k.t === "bullet" ? "• " : " ")).join("").replace(/\s+/g, " ").trim();
