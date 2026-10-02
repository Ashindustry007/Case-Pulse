"use client";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function SignOutButton() {
  return (
    <Button variant="ghost" size="sm" onClick={async () => { await api("/api/auth/logout", { method: "POST" }); window.location.assign("/login"); }}>
      <LogOut className="mr-1 h-4 w-4" /> Sign out
    </Button>
  );
}
