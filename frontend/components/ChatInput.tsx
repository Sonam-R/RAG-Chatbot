"use client";
import { useState } from "react";

export default function ChatInput({
  onSend, onStop, isLoading,
}: { onSend: (t: string) => void; onStop: () => void; isLoading: boolean }) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim() || isLoading) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="flex gap-2 border-t p-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={1}
        placeholder="Type a message…"
        className="flex-1 resize-none rounded-lg border p-2 text-sm"
      />
      {isLoading ? (
        <button onClick={onStop} className="rounded-lg bg-red-600 px-4 text-white">Stop</button>
      ) : (
        <button onClick={submit} disabled={!text.trim()} className="rounded-lg bg-blue-600 px-4 text-white disabled:opacity-50">Send</button>
      )}
    </div>
  );
}
