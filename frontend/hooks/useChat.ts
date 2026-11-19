"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, fetchConversation, streamChat } from "@/lib/api";

const STORAGE_KEY = "conversation_id";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Restore on refresh
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    fetchConversation(saved).then((convo) => {
      if (convo) {
        setConversationId(convo.id);
        setMessages(convo.messages);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    });
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;
      setError(null);
      setIsLoading(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: "" },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat({
          message: text,
          conversationId,
          signal: controller.signal,
          onEvent: (e) => {
            if (e.conversation_id) {
              setConversationId(e.conversation_id);
              localStorage.setItem(STORAGE_KEY, e.conversation_id);
            }
            const token = e.token;
            if (token) {
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = { ...last, content: last.content + token };
                return copy;
              });
            }
            if (e.error) setError(e.error);
          },
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError("Could not reach the server. Please try again.");
        }
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [conversationId, isLoading]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const newChat = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, send, stop, newChat };
}
