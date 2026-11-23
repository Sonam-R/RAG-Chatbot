"use client";
import { useCallback, useEffect, useState, type RefObject } from "react";
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type Document,
} from "@/lib/api";

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export default function DocumentPanel({
  fileInputRef,
  open,
}: {
  fileInputRef: RefObject<HTMLInputElement | null>;
  open: boolean;
}) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const rows = await listDocuments();
    setDocs(rows);
  }, []);

  useEffect(() => {
    refresh()
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Could not load documents"))
      .finally(() => setLoading(false));
  }, [refresh]);

  const handleFile = async (file: File) => {
    setError(null);
    if (!isPdf(file)) {
      setError("Only PDF files are supported");
      return;
    }
    setUploading(true);
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const onDelete = async (id: string) => {
    setError(null);
    setDeletingId(id);
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        disabled={uploading}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />
      {open && (
        <div className="absolute bottom-full left-0 z-10 mb-2 w-72 rounded-lg border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <p className="text-xs font-semibold">Documents</p>
          <p className="mt-1 text-xs text-gray-500">
            {uploading ? "Uploading…" : "PDF only. Use + to attach a file."}
          </p>
          {error && <div className="mt-2 rounded bg-red-50 px-2 py-1 text-xs text-red-700">{error}</div>}
          <div className="mt-2 max-h-48 overflow-y-auto">
            {loading ? (
              <p className="text-xs text-gray-400">Loading…</p>
            ) : docs.length === 0 ? (
              <p className="text-xs text-gray-400">No documents uploaded yet.</p>
            ) : (
              <ul className="space-y-1">
                {docs.map((d) => (
                  <li
                    key={d.id}
                    className="flex items-center gap-2 rounded-lg bg-gray-50 px-2 py-1.5 text-xs dark:bg-gray-800"
                  >
                    <span className="min-w-0 flex-1 truncate" title={d.filename}>
                      {d.filename}
                    </span>
                    <button
                      type="button"
                      aria-label={`Delete ${d.filename}`}
                      disabled={deletingId === d.id}
                      onClick={() => void onDelete(d.id)}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-950"
                    >
                      {deletingId === d.id ? (
                        <span className="text-[10px]">…</span>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
                          <path fillRule="evenodd" d="M8.75 1a.75.75 0 0 0-.75.75V3H4.5a.75.75 0 0 0 0 1.5h.31l.7 11.2A2.25 2.25 0 0 0 7.75 18h4.5a2.25 2.25 0 0 0 2.24-2.3l.7-11.2h.31a.75.75 0 0 0 0-1.5H12V1.75a.75.75 0 0 0-.75-.75h-2.5ZM10 6.5a.75.75 0 0 1 .75.75v6.5a.75.75 0 0 1-1.5 0v-6.5A.75.75 0 0 1 10 6.5Zm-2.75.75a.75.75 0 0 0-1.5 0v6.5a.75.75 0 0 0 1.5 0v-6.5Zm6.25-.75a.75.75 0 0 1 .75.75v6.5a.75.75 0 0 1-1.5 0v-6.5a.75.75 0 0 1 .75-.75Z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </>
  );
}
