import { newState, tokenize, type RichState, type Tok } from "@/lib/richtext";

export function renderTokens(toks: Tok[], key = "t") {
  return toks.map((k, i) => {
    if (k.t === "text") return k.b ? <strong key={`${key}${i}`} className="font-semibold text-foreground">{k.s}</strong> : <span key={`${key}${i}`}>{k.s}</span>;
    if (k.t === "bullet") return <span key={`${key}${i}`} className="mr-1.5 text-primary" aria-hidden>•</span>;
    return k.double
      ? <span key={`${key}${i}`} className="block h-2" aria-hidden />
      : <br key={`${key}${i}`} />;
  });
}

/** One string → formatted inline content. For multi-fragment text pass a shared `state` so bold carries over. */
export function RichText({ text, state }: { text: string; state?: RichState }) {
  return <>{renderTokens(tokenize(text, state ?? newState()))}</>;
}
