"use client";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function SignOutButton() {
  return (
    <Button
      variant="ghost" size="sm" aria-label="Sign out"
      onClick={async () => { await api("/api/auth/logout", { method: "POST" }); window.location.assign("/login"); }}
    >
      <LogOut className="size-4" /><span className="hidden sm:inline">Sign out</span>
    </Button>
  );
}
