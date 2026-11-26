"use client";

import { useEffect, useRef } from "react";
import { Send, Square } from "lucide-react";
import { MAX_MESSAGE_CHARS } from "@/lib/constants";
import { cn } from "@/lib/cn";

export default function ChatInput({
  value,
  onChange,
  onSend,
  onStop,
  isLoading,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  isLoading: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    const max = 6 * 24;
    el.style.height = `${Math.min(el.scrollHeight, max)}px`;
  }, [value]);

  const overLimit = value.length > MAX_MESSAGE_CHARS;
  const canSend = value.trim().length > 0 && !isLoading && !overLimit;

  return (
    <div
      className={cn(
        "border-t border-border bg-surface/95 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm",
        className,
      )}
    >
      <div className="w-full">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-soft">
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            rows={1}
            placeholder="Message your documents…"
            aria-label="Message"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (canSend) onSend();
              }
            }}
            className="max-h-[9rem] min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="inline-flex h-10 shrink-0 items-center gap-1 rounded-xl bg-danger px-3 text-sm font-medium text-white"
            >
              <Square className="h-3.5 w-3.5 fill-current" aria-hidden />
              Stop
            </button>
          ) : (
            <button
              type="button"
              disabled={!canSend}
              onClick={onSend}
              className={cn(
                "inline-flex h-10 shrink-0 items-center gap-1 rounded-xl bg-gradient-to-r from-accent to-accent-alt px-3 text-sm font-medium text-accent-foreground shadow-sm",
                !canSend && "opacity-50",
              )}
            >
              <Send className="h-3.5 w-3.5" aria-hidden />
              Send
            </button>
          )}
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-muted">
          <span>Enter to send · Shift+Enter for newline</span>
          <span className={overLimit ? "font-medium text-danger" : undefined}>
            {value.length}/{MAX_MESSAGE_CHARS}
          </span>
        </div>
      </div>
    </div>
  );
}