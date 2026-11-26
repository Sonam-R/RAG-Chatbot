"use client";

import { MessageSquarePlus, PanelLeftClose, PanelLeft } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import DocumentsPanel, { type DocumentsPanelProps } from "./DocumentsPanel";
import { cn } from "@/lib/cn";

type SidebarProps = DocumentsPanelProps & {
  onNewChat: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
};

export function Sidebar({
  onNewChat,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
  ...docProps
}: SidebarProps) {
  const inner = (
    <aside className="flex h-full w-[var(--sidebar-width)] max-w-[85vw] flex-col border-r border-border bg-surface-sidebar">
      <div className="flex items-center justify-between gap-2 border-b border-border bg-gradient-to-br from-accent-soft to-secondary-soft/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-alt text-sm font-semibold text-accent-foreground shadow-sm">
            R
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">RAG Chat</p>
            <p className="text-[11px] text-muted">Knowledge assistant</p>
          </div>
        </div>
        <button
          type="button"
          className="hidden rounded-lg border border-border p-1.5 text-muted hover:bg-surface-muted md:inline-flex"
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <div className="px-3 py-3">
        <button
          type="button"
          onClick={onNewChat}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground hover:bg-surface-muted"
        >
          <MessageSquarePlus className="h-4 w-4" aria-hidden />
          New chat
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col px-3 pb-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Documents</p>
        <DocumentsPanel {...docProps} />
      </div>

      <div className="mt-auto border-t border-border px-3 py-3">
        <ThemeToggle />
        <p className="mt-2 text-[11px] text-muted">Runs on local AI models</p>
      </div>
    </aside>
  );

  if (mobileOpen) {
    return (
      <>
        <button
          type="button"
          className="fixed inset-0 z-40 bg-foreground/40 md:hidden"
          aria-label="Close menu"
          onClick={onMobileClose}
        />
        <div className="fixed inset-y-0 left-0 z-50 md:hidden">{inner}</div>
      </>
    );
  }

  return (
    <div className={cn("hidden h-full shrink-0 md:block", collapsed && "md:w-0 md:overflow-hidden")}>
      {inner}
    </div>
  );
}