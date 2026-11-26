"use client";

import { ChevronDown, FileText } from "lucide-react";
import { Source } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useState } from "react";

export default function SourcesList({
  sources,
  highlightN,
  onHighlight,
}: {
  sources: Source[];
  highlightN: number | null;
  onHighlight: (n: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  if (sources.length === 0) return null;
  const panelId = "sources-panel";

  return (
    <div className="mt-3 border-t border-border pt-2">
      <button
        type="button"
        className="inline-flex items-center gap-1 text-xs font-semibold text-accent"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} aria-hidden />
        Sources ({sources.length})
      </button>
      {open && (
        <ul id={panelId} className="mt-2 space-y-1.5">
          {sources.map((s) => {
            const isOpen = expanded.has(s.n);
            return (
              <li
                key={s.n}
                id={`source-${s.n}`}
                className={cn(
                  "rounded-xl border border-border bg-surface-muted text-xs transition-colors",
                  highlightN === s.n && "ring-2 ring-accent",
                )}
              >
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-2 py-2 text-left"
                  onClick={() => {
                    onHighlight(s.n);
                    setExpanded((prev) => {
                      const n = new Set(prev);
                      if (n.has(s.n)) n.delete(s.n);
                      else n.add(s.n);
                      return n;
                    });
                  }}
                >
                  <FileText className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />
                  <span className="min-w-0 flex-1 truncate font-medium text-foreground">
                    [{s.n}] {s.filename} · Page {s.page}
                  </span>
                </button>
                {isOpen && (
                  <p className="border-t border-border px-2 py-2 text-muted leading-relaxed">{s.snippet}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}