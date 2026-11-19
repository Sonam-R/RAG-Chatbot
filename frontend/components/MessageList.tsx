"use client";
import { useEffect, useRef } from "react";
import { ChatMessage } from "@/lib/api";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        Ask me anything to get started.
      </div>
    );
  }
  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.map((m, i) => (
        <MessageBubble key={i} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
