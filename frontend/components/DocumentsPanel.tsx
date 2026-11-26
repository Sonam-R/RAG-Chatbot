"use client";

import { useState, type RefObject } from "react";
import {
  FileText,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
  FileType2,
} from "lucide-react";
import { ACCEPT_ATTR, MAX_UPLOAD_MB } from "@/lib/constants";
import { cn } from "@/lib/cn";
import type { Document } from "@/lib/api";
import type { UploadItem } from "@/hooks/useDocuments";
import { DeleteDocumentDialog } from "./DeleteDocumentDialog";

export type DocumentsPanelProps = {
  documents: Document[];
  isLoadingList: boolean;
  listError: string | null;
  uploads: UploadItem[];
  deletingIds: Set<string>;
  pickerOpening: boolean;
  fileInputRef: RefObject<HTMLInputElement | null>;
  onRefresh: () => Promise<void>;
  onUploadClick: () => void;
  onFileInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDropFiles: (files: FileList) => void;
  onDismissUpload: (id: string) => void;
  onRetryUpload: () => void;
  onConfirmDelete: (id: string, filename: string) => Promise<void>;
};

function formatDate(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function fileIcon(name: string) {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf")) return FileText;
  return FileType2;
}

export default function DocumentsPanel(props: DocumentsPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; filename: string } | null>(null);

  const {
    documents,
    isLoadingList,
    listError,
    uploads,
    deletingIds,
    pickerOpening,
    fileInputRef,
    onRefresh,
    onUploadClick,
    onFileInputChange,
    onDropFiles,
    onDismissUpload,
    onRetryUpload,
    onConfirmDelete,
  } = props;

  const busyDeleting = pendingDelete ? deletingIds.has(pendingDelete.id) : false;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT_ATTR}
        multiple
        className="sr-only"
        onChange={onFileInputChange}
        aria-hidden
      />

      <button
        type="button"
        onClick={onUploadClick}
        disabled={pickerOpening}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-3 py-2 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:opacity-70"
      >
        <Upload className="h-4 w-4" aria-hidden />
        Upload document
      </button>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files?.length) onDropFiles(e.dataTransfer.files);
        }}
        className={cn(
          "rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted transition-colors",
          dragOver && "border-accent bg-accent/5 text-foreground",
        )}
      >
        Drag & drop PDF, TXT, or MD (max {MAX_UPLOAD_MB} MB)
      </div>

      {uploads.length > 0 && (
        <ul className="space-y-2" aria-label="Upload progress">
          {uploads.map((u) => (
            <li key={u.id} className="rounded-lg border border-border bg-surface-muted px-2 py-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium text-foreground" title={u.filename}>
                  {u.filename}
                </span>
                {u.status === "uploading" && <span className="text-muted">{u.progress ?? 0}%</span>}
              </div>
              {u.status === "uploading" && <p className="mt-1 text-muted">Uploading…</p>}
              {u.status === "processing" && (
                <p className="mt-1 flex items-center gap-1 text-muted">
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                  Processing…
                </p>
              )}
              {u.status === "done" && <p className="mt-1 text-success">Done</p>}
              {u.status === "error" && (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="text-danger">{u.error}</span>
                  <button
                    type="button"
                    className="font-medium text-accent hover:underline"
                    onClick={() => {
                      onDismissUpload(u.id);
                      onRetryUpload();
                    }}
                  >
                    Retry
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoadingList ? (
          <ul className="space-y-2" aria-busy="true">
            {[1, 2, 3].map((i) => (
              <li key={i} className="h-14 animate-pulse rounded-xl bg-surface-muted" />
            ))}
          </ul>
        ) : listError ? (
          <div className="rounded-xl border border-danger/30 bg-danger-bg p-3 text-sm">
            <p className="text-foreground">{listError}</p>
            <button
              type="button"
              onClick={() => void onRefresh()}
              className="mt-2 inline-flex items-center gap-1 font-medium text-accent"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              Retry
            </button>
          </div>
        ) : documents.length === 0 ? (
          <p className="rounded-xl border border-border bg-surface-muted p-4 text-center text-sm text-muted">
            No documents yet. Upload a PDF, TXT, or MD file.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {documents.map((d) => {
              const Icon = fileIcon(d.filename);
              const deleting = deletingIds.has(d.id);
              return (
                <li
                  key={d.id}
                  className={cn(
                    "flex items-center gap-2 rounded-xl border border-border bg-surface px-2 py-2 transition-opacity",
                    deleting && "opacity-50",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0 text-muted" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground" title={d.filename}>
                      {d.filename}
                    </p>
                    <p className="text-[11px] text-muted">
                      {d.pages} pages · {d.chunks} chunks · {formatDate(d.created_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label={`Delete ${d.filename}`}
                    title={`Delete ${d.filename}`}
                    disabled={deleting}
                    onClick={(e) => {
                      e.stopPropagation();
                      setPendingDelete({ id: d.id, filename: d.filename });
                    }}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-danger hover:bg-danger-bg"
                  >
                    {deleting ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="h-4 w-4" aria-hidden />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <DeleteDocumentDialog
        filename={pendingDelete?.filename ?? ""}
        open={!!pendingDelete}
        busy={busyDeleting}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (!pendingDelete) return;
          void onConfirmDelete(pendingDelete.id, pendingDelete.filename).then(() =>
            setPendingDelete(null),
          );
        }}
      />
    </div>
  );
}