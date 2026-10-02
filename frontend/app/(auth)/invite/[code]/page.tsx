"use client";
import { use, useState } from "react";
import { Button } from "@/components/ui/button";
import { AuthShell } from "@/components/common/AuthShell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import type { UserOut } from "@/lib/types";

export default function InvitePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) { setError("Use at least 8 characters."); return; }
    try {
      await api<UserOut>(`/api/auth/invite/${encodeURIComponent(code)}/accept`, { json: { password, name: name || null } });
      window.location.assign("/provider/cases");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    }
  }

  return (
    <AuthShell title="Set up your access" subtitle="You were invited to view a case shared by a law firm.">
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-1.5"><Label htmlFor="name">Your name</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="pw">Choose a password</Label>
          <Input id="pw" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" size="lg" className="w-full">Continue</Button>
      </form>
    </AuthShell>
  );
}
