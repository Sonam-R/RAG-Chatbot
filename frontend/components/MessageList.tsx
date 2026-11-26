"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import { ChatMessage } from "@/lib/api";
import MessageBubble from "./MessageBubble";
import { EmptyState } from "./EmptyState";

export default function MessageList({
  messages,
  isLoading,
  liveStatus,
  onPickPrompt,
  noDocuments,
  onUploadHint,
}: {
  messages: ChatMessage[];
  isLoading: boolean;
  liveStatus: string | null;
  onPickPrompt: (t: string) => void;
  noDocuments: boolean;
  onUploadHint: () => void;
}) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [nearBottom, setNearBottom] = useState(true);

  const checkNearBottom = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const threshold = 120;
    setNearBottom(el.scrollHeight - el.scrollTop - el.clientHeight < threshold);
  }, []);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkNearBottom);
    return () => el.removeEventListener("scroll", checkNearBottom);
  }, [checkNearBottom]);

  useEffect(() => {
    if (nearBottom) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, nearBottom, liveStatus]);

  if (messages.length === 0) {
    return (
      <EmptyState onPickPrompt={onPickPrompt} noDocuments={noDocuments} onUploadHint={onUploadHint} />
    );
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={scrollerRef} className="h-full overflow-y-auto overflow-x-hidden px-4 py-4">
        <div className="w-full space-y-4">
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              message={
                i === messages.length - 1 && m.role === "assistant" && liveStatus && !m.content
                  ? { ...m, statusText: liveStatus }
                  : m
              }
              isStreaming={isLoading && i === messages.length - 1 && m.role === "assistant" && !!m.content}
              showTyping={isLoading && i === messages.length - 1 && m.role === "assistant" && !m.content && !liveStatus}
            />
          ))}
          <div ref={endRef} />
        </div>
      </div>
      {!nearBottom && (
        <button
          type="button"
          onClick={() => {
            setNearBottom(true);
            endRef.current?.scrollIntoView({ behavior: "smooth" });
          }}
          className="absolute bottom-4 left-1/2 z-10 inline-flex -translate-x-1/2 items-center gap-1 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium shadow-soft"
        >
          <ArrowDown className="h-3.5 w-3.5" aria-hidden />
          Jump to latest
        </button>
      )}
    </div>
  );
}