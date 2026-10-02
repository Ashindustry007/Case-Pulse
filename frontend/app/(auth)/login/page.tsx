"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AuthShell } from "@/components/common/AuthShell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { HOME } from "@/lib/route-guard";
import type { UserOut } from "@/lib/types";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const user = await api<UserOut>("/api/auth/login", { json: { email, password } });
      const next = new URLSearchParams(window.location.search).get("next");
      const home = HOME[user.role];
      window.location.assign(next && next.startsWith(home) ? next : home);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Wrong email or password." : String(err));
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Case Pulse" subtitle="Every case, digested — with the source one click away.">
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5"><Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" size="lg" className="w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
        <p className="text-center text-xs text-muted-foreground">First time? Use the invite link from your email.</p>
      </form>
    </AuthShell>
  );
}
