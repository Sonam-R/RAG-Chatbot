"use client";

import { AlertCircle, X } from "lucide-react";

export function ErrorBanner({
  message,
  onRetry,
  onDismiss,
  retryDisabled,
}: {
  message: string;
  onRetry: () => void;
  onDismiss: () => void;
  retryDisabled?: boolean;
}) {
  return (
    <div
      role="alert"
      className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-2 rounded-xl border border-danger/40 bg-danger-bg px-3 py-2 text-sm text-foreground"
    >
      <AlertCircle className="h-4 w-4 shrink-0 text-danger" aria-hidden />
      <span className="flex-1">{message}</span>
      {!retryDisabled && (
        <button
          type="button"
          onClick={() => void onRetry()}
          className="rounded-lg border border-danger/50 px-2 py-1 text-xs font-medium hover:bg-danger/10"
        >
          Retry
        </button>
      )}
      <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="rounded p-1 hover:bg-danger/10">
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}