"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

export function DeleteDocumentDialog({
  filename,
  open,
  onCancel,
  onConfirm,
  busy,
}: {
  filename: string;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    cancelRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
  <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-doc-title"
    >
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-4 shadow-soft">
        <h2 id="delete-doc-title" className="text-base font-semibold text-foreground">
          Delete document?
        </h2>
        <p className="mt-2 text-sm text-muted">
          <span className="font-medium text-foreground">{filename}</span>
          <br />
          This removes the document and its search data. This cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-surface-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={cn(
              "rounded-lg bg-danger px-3 py-1.5 text-sm font-medium text-surface",
              busy && "opacity-60",
            )}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}