"use client";
import { ThemeProvider as NextThemes } from "next-themes";

/** Dark by default; the choice is remembered (localStorage) and applied as a `dark` class on <html>. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemes attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
      {children}
    </NextThemes>
  );
}
