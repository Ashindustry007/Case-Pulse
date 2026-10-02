import { Skeleton } from "@/components/ui/skeleton";

export function Loading({ lines = 3 }: { lines?: number }) {
  return <div className="space-y-2">{Array.from({ length: lines }, (_, i) => <Skeleton key={i} className="h-4 w-full" />)}</div>;
}

export function ErrorNote({ error }: { error?: { message: string } | null }) {
  if (!error) return null;
  return <p className="text-sm text-destructive">Couldn&apos;t load: {error.message}</p>;
}

export function NotFoundText() {
  return <span className="italic text-muted-foreground">not found in file</span>;
}
