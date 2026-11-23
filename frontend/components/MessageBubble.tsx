"use client";
import { Children, Fragment, isValidElement, useState, type HTMLAttributes, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import { ChatMessage, Source } from "@/lib/api";
import SourcesList from "./SourcesList";

const MARKER = /\[(\d+)\]/g;

function splitMarkers(
  text: string,
  sourcesByN: Map<number, Source>,
  onCite: (n: number) => void,
): ReactNode[] {
  const parts: ReactNode[] = [];
  let last = 0;
  const re = new RegExp(MARKER.source, "g");
  let match: RegExpExecArray | null;
  while ((match = re.exec(text))) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const n = Number(match[1]);
    if (sourcesByN.has(n)) {
      parts.push(
        <button
          key={`${match.index}-${n}`}
          type="button"
          title={sourcesByN.get(n)?.filename}
          onClick={() => onCite(n)}
          className="mx-0.5 inline-flex h-4 min-w-4 translate-y-[-0.2em] items-center justify-center rounded bg-blue-600 px-1 text-[10px] font-semibold text-white"
        >
          {n}
        </button>,
      );
    } else {
      parts.push(match[0]);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function citeChildren(
  children: ReactNode,
  sourcesByN: Map<number, Source>,
  onCite: (n: number) => void,
): ReactNode {
  return Children.map(children, (child, i) => {
    if (typeof child === "string") {
      return <Fragment key={i}>{splitMarkers(child, sourcesByN, onCite)}</Fragment>;
    }
    if (isValidElement<{ children?: ReactNode }>(child) && child.props.children) {
      return child;
    }
    return child;
  });
}

function citeTag(Tag: "p" | "li" | "blockquote" | "h1" | "h2" | "h3" | "h4") {
  return function Cited({
    children,
    sourcesByN,
    onCite,
    ...props
  }: HTMLAttributes<HTMLElement> & {
    sourcesByN: Map<number, Source>;
    onCite: (n: number) => void;
  }) {
    return (
      <Tag {...props}>{citeChildren(children, sourcesByN, onCite)}</Tag>
    );
  };
}

export default function MessageBubble({
  message,
  isThinking = false,
}: {
  message: ChatMessage;
  isThinking?: boolean;
}) {
  const isUser = message.role === "user";
  const sources = message.sources ?? null;
  const [open, setOpen] = useState(false);
  const [highlightN, setHighlightN] = useState<number | null>(null);
  const sourcesByN = new Map((sources ?? []).map((s) => [s.n, s]));

  const onCite = (n: number) => {
    setOpen(true);
    setHighlightN(n);
  };

  const markdownComponents = {
    p: (props: HTMLAttributes<HTMLParagraphElement>) =>
      citeTag("p")({ ...props, sourcesByN, onCite }),
    li: (props: HTMLAttributes<HTMLLIElement>) =>
      citeTag("li")({ ...props, sourcesByN, onCite }),
    blockquote: (props: HTMLAttributes<HTMLQuoteElement>) =>
      citeTag("blockquote")({ ...props, sourcesByN, onCite }),
    h1: (props: HTMLAttributes<HTMLHeadingElement>) =>
      citeTag("h1")({ ...props, sourcesByN, onCite }),
    h2: (props: HTMLAttributes<HTMLHeadingElement>) =>
      citeTag("h2")({ ...props, sourcesByN, onCite }),
    h3: (props: HTMLAttributes<HTMLHeadingElement>) =>
      citeTag("h3")({ ...props, sourcesByN, onCite }),
    h4: (props: HTMLAttributes<HTMLHeadingElement>) =>
      citeTag("h4")({ ...props, sourcesByN, onCite }),
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          <>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown components={markdownComponents}>{message.content}</ReactMarkdown>
            </div>
            {sources && sources.length > 0 && (
              <SourcesList
                sources={sources}
                open={open}
                onToggle={() => setOpen((v) => !v)}
                highlightN={highlightN}
              />
            )}
          </>
        ) : isThinking ? (
          <span className="animate-pulse">Thinking…</span>
        ) : (
          <span className="text-gray-500">No response</span>
        )}
      </div>
    </div>
  );
}
