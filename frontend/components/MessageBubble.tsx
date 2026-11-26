"use client";

import {
  Children,
  Fragment,
  isValidElement,
  useState,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Check, Copy, Info, AlertTriangle } from "lucide-react";
import { ChatMessage, Source } from "@/lib/api";
import SourcesList from "./SourcesList";
import { cn } from "@/lib/cn";
import { useToast } from "@/hooks/useToast";

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
          className="mx-0.5 inline-flex h-4 min-w-4 translate-y-[-0.15em] items-center justify-center rounded bg-accent px-1 text-[10px] font-semibold text-accent-foreground"
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

function citeChildren(children: ReactNode, sourcesByN: Map<number, Source>, onCite: (n: number) => void): ReactNode {
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
    return <Tag {...props}>{citeChildren(children, sourcesByN, onCite)}</Tag>;
  };
}

function PreWithCopy({ children, ...props }: HTMLAttributes<HTMLPreElement> & { children?: ReactNode }) {
  const { toast } = useToast();
  const text =
    typeof children === "object" &&
    isValidElement<{ children?: ReactNode }>(children) &&
    children.props.children
      ? String(children.props.children)
      : String(children ?? "");
  return (
    <div className="group relative my-2">
      <pre {...props} className="overflow-x-auto rounded-lg bg-surface-muted p-3 text-xs">
        {children}
      </pre>
      <button
        type="button"
        className="absolute right-2 top-2 rounded-md border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-muted hover:text-foreground"
        onClick={() => {
          void navigator.clipboard.writeText(text.trim());
          toast("Copied to clipboard", "success");
        }}
      >
        Copy
      </button>
    </div>
  );
}

export default function MessageBubble({
  message,
  isStreaming = false,
  showTyping = false,
}: {
  message: ChatMessage;
  isStreaming?: boolean;
  showTyping?: boolean;
}) {
  const { toast } = useToast();
  const isUser = message.role === "user";
  const sources = message.sources ?? null;
  const [highlightN, setHighlightN] = useState<number | null>(null);
  const sourcesByN = new Map((sources ?? []).map((s) => [s.n, s]));

  const onCite = (n: number) => {
    setHighlightN(n);
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const markdownComponents = {
    p: (props: HTMLAttributes<HTMLParagraphElement>) => citeTag("p")({ ...props, sourcesByN, onCite }),
    li: (props: HTMLAttributes<HTMLLIElement>) => citeTag("li")({ ...props, sourcesByN, onCite }),
    blockquote: (props: HTMLAttributes<HTMLQuoteElement>) =>
      citeTag("blockquote")({ ...props, sourcesByN, onCite }),
    h1: (props: HTMLAttributes<HTMLHeadingElement>) => citeTag("h1")({ ...props, sourcesByN, onCite }),
    h2: (props: HTMLAttributes<HTMLHeadingElement>) => citeTag("h2")({ ...props, sourcesByN, onCite }),
    h3: (props: HTMLAttributes<HTMLHeadingElement>) => citeTag("h3")({ ...props, sourcesByN, onCite }),
    h4: (props: HTMLAttributes<HTMLHeadingElement>) => citeTag("h4")({ ...props, sourcesByN, onCite }),
    pre: PreWithCopy,
  };

  const verification = message.verification;
  const unverified = verification?.status === "unverified";

  return (
    <div className={cn("group flex gap-2", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div
          className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border bg-secondary-soft text-secondary"
          aria-hidden
        >
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[min(100%,42rem)] rounded-2xl px-4 py-2.5 text-sm shadow-soft",
          isUser &&
            "border-0 bg-gradient-to-br from-accent via-accent to-accent-alt text-accent-foreground shadow-sm",
          !isUser && !message.isRefusal && "border border-border bg-surface text-foreground",
          !isUser && message.isRefusal && "border border-border bg-surface-muted text-foreground",
        )}
      >
        {!isUser && message.statusText && !message.content && (
          <p className="mb-2 flex items-center gap-2 text-xs text-muted" role="status" aria-live="polite">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
            {message.statusText}
          </p>
        )}

        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          <>
            {message.isRefusal && (
              <p className="mb-2 flex items-start gap-2 text-xs text-muted">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                Try rephrasing or upload a document that covers this topic.
              </p>
            )}
            <div className="prose prose-sm prose-slate dark:prose-invert max-w-none [&_table]:block [&_table]:overflow-x-auto">
              <ReactMarkdown components={markdownComponents}>{message.content}</ReactMarkdown>
            </div>
            {isStreaming && <span className="caret-blink ml-0.5 inline-block h-4 w-0.5 bg-accent align-middle" />}
            {unverified && (
              <p
                className="mt-2 inline-flex items-center gap-1 rounded-lg bg-warning-bg px-2 py-1 text-xs text-warning"
                title={verificationTooltip(verification)}
              >
                <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
                Some citations could not be verified
              </p>
            )}
            {verification?.status === "ok" && !isStreaming && (
              <span className="mt-2 inline-flex items-center gap-1 text-[11px] text-success" title="Citations verified">
                <Check className="h-3 w-3" aria-hidden />
                Verified
              </span>
            )}
            {sources && sources.length > 0 && (
              <SourcesList sources={sources} highlightN={highlightN} onHighlight={setHighlightN} />
            )}
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard.writeText(message.content);
                toast("Answer copied", "success");
              }}
              className="mt-2 inline-flex items-center gap-1 text-[11px] text-muted opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
            >
              <Copy className="h-3 w-3" aria-hidden />
              Copy
            </button>
          </>
        ) : showTyping ? (
          <span className="flex items-center gap-1 text-muted" role="status">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:300ms]" />
          </span>
        ) : (
          <span className="text-muted">No response</span>
        )}
      </div>
    </div>
  );
}

function verificationTooltip(v: ChatMessage["verification"]): string {
  if (!v) return "";
  const parts: string[] = [];
  if (v.invalid_citations?.length) parts.push(`Invalid cites: [${v.invalid_citations.join(", ")}]`);
  if (v.missing_citation) parts.push("Missing citation");
  if (v.unsupported_numbers?.length) parts.push(`Unsupported numbers: ${v.unsupported_numbers.join(", ")}`);
  return parts.join(" · ") || "Unverified";
}