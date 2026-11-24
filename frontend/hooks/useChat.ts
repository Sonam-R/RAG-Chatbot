"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, fetchConversation, streamChat } from "@/lib/api";

const STORAGE_KEY = "conversation_id";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useDocuments, setUseDocuments] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);

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

  const runStream = useCallback(
    async (text: string, appendUser: boolean) => {
      setError(null);
      setIsLoading(true);
      lastUserMessageRef.current = text;

      if (appendUser) {
        setMessages((prev) => [
          ...prev,
          { role: "user", content: text },
          { role: "assistant", content: "", sources: null },
        ]);
      } else {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last?.role === "assistant") {
            copy[copy.length - 1] = { ...last, content: "", sources: null };
          } else {
            copy.push({ role: "assistant", content: "", sources: null });
          }
          return copy;
        });
      }

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat({
          message: text,
          conversationId,
          useDocuments,
          signal: controller.signal,
          onSources: (sources) => {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (!last || last.role !== "assistant") return prev;
              copy[copy.length - 1] = { ...last, sources };
              return copy;
            });
          },
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
                if (!last || last.role !== "assistant") return prev;
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
    [conversationId, useDocuments]
  );

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;
      await runStream(text.trim(), true);
    },
    [isLoading, runStream]
  );

  const retry = useCallback(async () => {
    const text = lastUserMessageRef.current;
    if (!text || isLoading) return;
    await runStream(text, false);
  }, [isLoading, runStream]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const newChat = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setConversationId(null);
    setMessages([]);
    setError(null);
    lastUserMessageRef.current = null;
  }, []);

  return {
    messages,
    isLoading,
    error,
    send,
    retry,
    stop,
    newChat,
    useDocuments,
    setUseDocuments,
  };
}