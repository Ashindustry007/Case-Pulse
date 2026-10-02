const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/** Date-only strings are calendar dates, not UTC midnights: parse them in local time. */
export function parseISODate(iso: string): Date {
  if (DATE_ONLY.test(iso)) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(iso);
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  return parseISODate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return "";
  return parseISODate(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function fmtMoney(n?: number | null): string {
  if (n == null) return "";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function fmtMoneyShort(n: number): string {
  if (Math.abs(n) < 1000) return `$${Math.round(n)}`;
  const k = n / 1000;
  return `$${Number.isInteger(Math.round(k * 10) / 10) ? Math.round(k) : (Math.round(k * 10) / 10).toFixed(1)}k`;
}

export function daysAgo(iso: string, now: Date = new Date()): number {
  const d = parseISODate(iso);
  const a = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const b = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  return Math.round((b - a) / 86_400_000);
}

export const usd = (n: number) => `$${n.toFixed(2)}`;
