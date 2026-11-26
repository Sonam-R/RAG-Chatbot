"use client";

import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/cn";

export function ToastViewport() {
  const { toasts, dismiss } = useToast();
  if (toasts.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-4 z-[100] flex w-[min(100%,22rem)] flex-col gap-2"
      aria-live="polite"
      role="status"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex items-start gap-2 rounded-xl border px-3 py-2 text-sm shadow-soft",
            t.variant === "success" && "border-success/30 bg-surface text-foreground",
            t.variant === "error" && "border-danger/40 bg-danger-bg text-foreground",
            t.variant === "info" && "border-border bg-surface text-foreground",
          )}
        >
          {t.variant === "success" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />}
          {t.variant === "error" && <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />}
          {t.variant === "info" && <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" aria-hidden />}
          <span className="flex-1">{t.message}</span>
          <button
            type="button"
            className="text-muted hover:text-foreground text-xs"
            onClick={() => dismiss(t.id)}
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}