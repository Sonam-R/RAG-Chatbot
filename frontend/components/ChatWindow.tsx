"use client";
import { useChat } from "@/hooks/useChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

export default function ChatWindow() {
  const {
    messages,
    isLoading,
    error,
    send,
    retry,
    stop,
    newChat,
    useDocuments,
    setUseDocuments,
  } = useChat();
  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col">
      <header className="flex items-center justify-between border-b p-3">
        <h1 className="font-semibold">RAG Chatbot</h1>
        <button onClick={newChat} className="text-sm text-blue-600">
          New chat
        </button>
      </header>
      <MessageList messages={messages} isLoading={isLoading} />
      {error && (
        <div className="flex flex-wrap items-center gap-3 bg-red-50 px-4 py-2 text-sm text-red-700">
          <span>{error}</span>
          {!isLoading && (
            <button
              type="button"
              onClick={() => void retry()}
              className="rounded border border-red-300 px-2 py-0.5 text-red-800 hover:bg-red-100"
            >
              Retry
            </button>
          )}
        </div>
      )}
      <label className="flex items-center gap-2 border-t px-3 pt-2 text-sm">
        <input
          type="checkbox"
          checked={useDocuments}
          onChange={(e) => setUseDocuments(e.target.checked)}
        />
        Answer from documents
      </label>
      <ChatInput onSend={send} onStop={stop} isLoading={isLoading} />
    </div>
  );
}
