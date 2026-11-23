"use client";
import { useRef, useState } from "react";
import DocumentPanel from "./DocumentPanel";

export default function ChatInput({
  onSend, onStop, isLoading,
}: { onSend: (t: string) => void; onStop: () => void; isLoading: boolean }) {
  const [text, setText] = useState("");
  const [docsOpen, setDocsOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!text.trim() || isLoading) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="flex items-end gap-2 p-3">
      <div className="relative">
        <button
          type="button"
          aria-label="Upload PDF"
          aria-expanded={docsOpen}
          title="Upload PDF"
          onClick={() => {
            setDocsOpen(true);
            fileInputRef.current?.click();
          }}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border text-xl leading-none text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          +
        </button>
        <DocumentPanel fileInputRef={fileInputRef} open={docsOpen} />
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        onFocus={() => setDocsOpen(false)}
        rows={1}
        placeholder="Type a message…"
        className="flex-1 resize-none rounded-lg border p-2 text-sm"
      />
      {isLoading ? (
        <button onClick={onStop} className="h-10 rounded-lg bg-red-600 px-4 text-white">Stop</button>
      ) : (
        <button onClick={submit} disabled={!text.trim()} className="h-10 rounded-lg bg-blue-600 px-4 text-white disabled:opacity-50">Send</button>
      )}
    </div>
  );
}
