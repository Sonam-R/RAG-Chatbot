"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES } from "@/lib/constants";
import {
  deleteDocument,
  listDocuments,
  uploadDocumentXHR,
  type Document,
} from "@/lib/api";
import { useToast } from "./useToast";

export type UploadStatus = "uploading" | "processing" | "done" | "error";

export type UploadItem = {
  id: string;
  filename: string;
  size: number;
  status: UploadStatus;
  error?: string;
  progress?: number;
};

function extOk(name: string): boolean {
  const lower = name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((e) => lower.endsWith(e));
}

function validateClient(file: File): string | null {
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_UPLOAD_BYTES) return `File exceeds ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB.`;
  if (!extOk(file.name)) return "Unsupported type. Use PDF, TXT, or MD.";
  return null;
}

const MAX_PARALLEL = 2;

export function useDocuments() {
  const { toast } = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [pickerOpening, setPickerOpening] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeUploads = useRef(0);
  const queue = useRef<File[]>([]);
  const drainQueueRef = useRef<() => void>(() => undefined);

  const refresh = useCallback(async () => {
    setListError(null);
    const rows = await listDocuments();
    setDocuments(rows);
  }, []);

  useEffect(() => {
    let mounted = true;
    void listDocuments()
      .then((rows) => {
        if (mounted) setDocuments(rows);
      })
      .catch((err) => {
        if (mounted) {
          setListError(err instanceof Error ? err.message : "Could not load documents");
        }
      })
      .finally(() => {
        if (mounted) setIsLoadingList(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const updateUpload = useCallback((id: string, patch: Partial<UploadItem>) => {
    setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, ...patch } : u)));
  }, []);

  const removeUploadLater = useCallback((id: string) => {
    window.setTimeout(() => {
      setUploads((prev) => prev.filter((u) => u.id !== id));
    }, 2000);
  }, []);

  const runOneUpload = useCallback(
    async (file: File) => {
      const id = crypto.randomUUID();
      const item: UploadItem = {
        id,
        filename: file.name,
        size: file.size,
        status: "uploading",
        progress: 0,
      };
      setUploads((prev) => [...prev, item]);

      const clientErr = validateClient(file);
      if (clientErr) {
        updateUpload(id, { status: "error", error: clientErr });
        toast(clientErr, "error");
        return;
      }

      try {
        await uploadDocumentXHR(file, (loaded, total) => {
          updateUpload(id, {
            status: "uploading",
            progress: Math.round((loaded / total) * 100),
          });
        });
        updateUpload(id, { status: "processing", progress: 100 });
        await refresh();
        updateUpload(id, { status: "done" });
        toast(`Uploaded ${file.name}`, "success");
        removeUploadLater(id);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        updateUpload(id, { status: "error", error: msg });
        toast(msg, "error");
      }
    },
    [refresh, removeUploadLater, toast, updateUpload],
  );

  const runOneUploadRef = useRef(runOneUpload);
  useEffect(() => {
    runOneUploadRef.current = runOneUpload;
  }, [runOneUpload]);

  const drainQueue = useCallback(() => {
    while (activeUploads.current < MAX_PARALLEL && queue.current.length > 0) {
      const file = queue.current.shift();
      if (!file) break;
      activeUploads.current += 1;
      void runOneUploadRef.current(file).finally(() => {
        activeUploads.current -= 1;
        drainQueueRef.current();
      });
    }
  }, []);

  useEffect(() => {
    drainQueueRef.current = drainQueue;
  }, [drainQueue]);

  const upload = useCallback(
    (files: FileList | File[]) => {
      queue.current.push(...Array.from(files));
      drainQueue();
    },
    [drainQueue],
  );

  const dismissUpload = useCallback((uploadId: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== uploadId));
  }, []);

  const remove = useCallback(
    async (id: string, filename: string) => {
      const snapshot = documents;
      setDeletingIds((s) => new Set(s).add(id));
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      try {
        await deleteDocument(id);
        toast(`Deleted ${filename}`, "success");
        await refresh().catch(() => undefined);
      } catch (err) {
        setDocuments(snapshot);
        const msg = err instanceof Error ? err.message : "Delete failed";
        toast(msg, "error");
        throw err;
      } finally {
        setDeletingIds((s) => {
          const n = new Set(s);
          n.delete(id);
          return n;
        });
      }
    },
    [documents, refresh, toast],
  );

  const openFilePicker = useCallback(() => {
    setPickerOpening(true);
    fileInputRef.current?.click();
    window.setTimeout(() => setPickerOpening(false), 400);
  }, []);

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files?.length) upload(files);
      e.target.value = "";
      setPickerOpening(false);
    },
    [upload],
  );

  return {
    documents,
    isLoadingList,
    listError,
    uploads,
    deletingIds,
    pickerOpening,
    fileInputRef,
    upload,
    remove,
    refresh,
    dismissUpload,
    openFilePicker,
    onFileInputChange,
  };
}