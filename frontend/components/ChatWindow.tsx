"use client";
import { useChat } from "@/hooks/useChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

export default function ChatWindow() {
  const { messages, isLoading, error, send, stop, newChat } = useChat();
  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col">
      <header className="flex items-center justify-between border-b p-3">
        <h1 className="font-semibold">RAG Chatbot</h1>
        <button onClick={newChat} className="text-sm text-blue-600">New chat</button>
      </header>
      <MessageList messages={messages} isLoading={isLoading} />
      {error && <div className="bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}
      <ChatInput onSend={send} onStop={stop} isLoading={isLoading} />
    </div>
  );
}
