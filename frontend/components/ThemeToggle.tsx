"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { resolvedDark, toggle } = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface-muted hover:text-foreground"
      aria-label={resolvedDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {resolvedDark ? <Sun className="h-3.5 w-3.5" aria-hidden /> : <Moon className="h-3.5 w-3.5" aria-hidden />}
      {resolvedDark ? "Light" : "Dark"}
    </button>
  );
}