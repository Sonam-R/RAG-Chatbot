"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChatMessage,
  fetchConversation,
  streamChat,
  type VerificationResult,
} from "@/lib/api";

const STORAGE_KEY = "conversation_id";
const REFUSAL_RE = /couldn'?t find that in the uploaded documents/i;

function isRefusal(text: string): boolean {
  return REFUSAL_RE.test(text);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDismissed, setErrorDismissed] = useState(false);
  const [useDocuments, setUseDocuments] = useState(true);
  const [liveStatus, setLiveStatus] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    fetchConversation(saved).then((convo) => {
      if (convo) {
        conversationIdRef.current = convo.id;
        setConversationId(convo.id);
        setMessages(
          convo.messages.map((m) => ({
            ...m,
            isRefusal: m.role === "assistant" ? isRefusal(m.content) : false,
          })),
        );
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    });
  }, []);

  const patchLastAssistant = useCallback(
    (patch: Partial<ChatMessage>) => {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (!last || last.role !== "assistant") return prev;
        copy[copy.length - 1] = { ...last, ...patch };
        return copy;
      });
    },
    [],
  );

  const runStream = useCallback(
    async (text: string, appendUser: boolean) => {
      setError(null);
      setErrorDismissed(false);
      setIsLoading(true);
      setLiveStatus(null);
      lastUserMessageRef.current = text;

      if (appendUser) {
        setMessages((prev) => [
          ...prev,
          { role: "user", content: text },
          { role: "assistant", content: "", sources: null, statusText: null, verification: null },
        ]);
      } else {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last?.role === "assistant") {
            copy[copy.length - 1] = {
              ...last,
              content: "",
              sources: null,
              statusText: null,
              verification: null,
              isRefusal: false,
            };
          } else {
            copy.push({
              role: "assistant",
              content: "",
              sources: null,
              statusText: null,
              verification: null,
            });
          }
          return copy;
        });
      }

      const controller = new AbortController();
      abortRef.current = controller;
      let gotToken = false;

      try {
        await streamChat({
          message: text,
          conversationId: conversationIdRef.current ?? conversationId,
          useDocuments,
          signal: controller.signal,
          onSources: (sources) => {
            patchLastAssistant({ sources });
          },
          onEvent: (e) => {
            if (e.conversation_id) {
              conversationIdRef.current = e.conversation_id;
              setConversationId(e.conversation_id);
              localStorage.setItem(STORAGE_KEY, e.conversation_id);
            }
            if (e.status) {
              setLiveStatus(e.status);
              if (!gotToken) patchLastAssistant({ statusText: e.status });
            }
            if (e.verification) {
              patchLastAssistant({ verification: e.verification as VerificationResult });
              setLiveStatus(null);
            }
            const token = e.token;
            if (token) {
              gotToken = true;
              setLiveStatus(null);
              patchLastAssistant({ statusText: null });
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (!last || last.role !== "assistant") return prev;
                const content = last.content + token;
                copy[copy.length - 1] = {
                  ...last,
                  content,
                  isRefusal: isRefusal(content),
                };
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
        setLiveStatus(null);
        abortRef.current = null;
      }
    },
    [conversationId, patchLastAssistant, useDocuments],
  );

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;
      await runStream(text.trim(), true);
    },
    [isLoading, runStream],
  );

  const retry = useCallback(async () => {
    const text = lastUserMessageRef.current;
    if (!text || isLoading) return;
    setErrorDismissed(false);
    await runStream(text, false);
  }, [isLoading, runStream]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const newChat = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    conversationIdRef.current = null;
    setConversationId(null);
    setMessages([]);
    setError(null);
    setErrorDismissed(false);
    lastUserMessageRef.current = null;
  }, []);

  const dismissError = useCallback(() => setErrorDismissed(true), []);

  return {
    messages,
    isLoading,
    error: errorDismissed ? null : error,
    send,
    retry,
    stop,
    newChat,
    useDocuments,
    setUseDocuments,
    dismissError,
    liveStatus,
  };
}