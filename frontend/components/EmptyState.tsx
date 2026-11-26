"use client";

import { EXAMPLE_PROMPTS } from "@/lib/constants";
import { FileUp } from "lucide-react";

export function EmptyState({
  onPickPrompt,
  noDocuments,
  onUploadHint,
}: {
  onPickPrompt: (text: string) => void;
  noDocuments: boolean;
  onUploadHint: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-8 text-center">
      <h2 className="text-lg font-semibold text-foreground">Ask your documents</h2>
      <p className="mt-1 max-w-md text-sm text-muted">
        Grounded answers from your uploaded PDFs and text files, with cited sources.
      </p>
      {noDocuments && (
        <button
          type="button"
          onClick={onUploadHint}
          className="mt-4 inline-flex items-center gap-2 rounded-xl border border-accent/40 bg-accent/10 px-3 py-2 text-sm font-medium text-accent"
        >
          <FileUp className="h-4 w-4" aria-hidden />
          Upload a document to get started
        </button>
      )}
      <div className="mt-6 grid w-full max-w-lg gap-2 sm:grid-cols-1">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPickPrompt(p)}
            className="rounded-xl border border-border bg-gradient-to-br from-surface to-accent-soft/30 px-4 py-3 text-left text-sm text-foreground shadow-soft transition-colors hover:border-accent hover:from-accent-soft/40"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}