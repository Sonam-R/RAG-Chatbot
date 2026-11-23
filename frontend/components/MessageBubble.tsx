import ReactMarkdown from "react-markdown";
import { ChatMessage } from "@/lib/api";

export default function MessageBubble({
  message,
  isThinking = false,
}: {
  message: ChatMessage;
  isThinking?: boolean;
}) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : isThinking ? (
          <span className="animate-pulse">Thinking…</span>
        ) : (
          <span className="text-gray-500">No response</span>
        )}
      </div>
    </div>
  );
}
