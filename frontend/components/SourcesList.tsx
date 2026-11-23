"use client";
import { Source } from "@/lib/api";

export default function SourcesList({
  sources,
  open,
  onToggle,
  highlightN,
}: {
  sources: Source[];
  open: boolean;
  onToggle: () => void;
  highlightN: number | null;
}) {
  if (sources.length === 0) return null;
  const panelId = "sources-panel";
  return (
    <div className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-700">
      <button
        type="button"
        className="text-xs font-medium text-blue-600"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
      >
        Sources ({sources.length})
      </button>
      {open && (
        <ul id={panelId} className="mt-2 space-y-2">
          {sources.map((s) => (
            <li
              key={s.n}
              id={`source-${s.n}`}
              title={`Score ${s.score}`}
              className={`rounded-lg px-2 py-1 text-xs ${
                highlightN === s.n ? "bg-blue-50 ring-1 ring-blue-400 dark:bg-blue-950" : "bg-gray-50 dark:bg-gray-800"
              }`}
            >
              <div className="font-medium text-gray-800 dark:text-gray-100">
                [{s.n}] {s.filename}, page {s.page}
              </div>
              <p className="mt-0.5 text-gray-600 dark:text-gray-300">{s.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
