"use client";

import { useState } from "react";
import { Menu, Search } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { Sidebar } from "./Sidebar";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import { ErrorBanner } from "./ErrorBanner";
import { cn } from "@/lib/cn";

export default function ChatWindow() {
  const chat = useChat();
  const docs = useDocuments();
  const [input, setInput] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);

  const send = () => {
    const t = input.trim();
    if (!t) return;
    void chat.send(t);
    setInput("");
  };

  return (
    <div className="flex h-[100dvh] min-h-0 w-full overflow-hidden bg-background">
      <Sidebar
        documents={docs.documents}
        isLoadingList={docs.isLoadingList}
        listError={docs.listError}
        uploads={docs.uploads}
        deletingIds={docs.deletingIds}
        pickerOpening={docs.pickerOpening}
        fileInputRef={docs.fileInputRef}
        onRefresh={docs.refresh}
        onUploadClick={docs.openFilePicker}
        onFileInputChange={docs.onFileInputChange}
        onDropFiles={(files) => docs.upload(files)}
        onDismissUpload={docs.dismissUpload}
        onRetryUpload={docs.openFilePicker}
        onConfirmDelete={docs.remove}
        onNewChat={chat.newChat}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
        mobileOpen={mobileNav}
        onMobileClose={() => setMobileNav(false)}
      />

      <div className="flex min-h-0 min-w-0 flex-1 justify-center overflow-hidden px-2 sm:px-4">
        <div className="chat-column flex flex-col rounded-none border-x border-border bg-surface shadow-soft md:my-3 md:max-h-[calc(100dvh-1.5rem)] md:rounded-2xl md:border">
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-gradient-to-r from-accent-soft/80 via-surface to-secondary-soft/50 px-4 py-3 md:rounded-t-2xl">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-lg border border-border p-2 text-muted md:hidden"
              aria-label="Open documents menu"
              onClick={() => setMobileNav(true)}
            >
              <Menu className="h-4 w-4" />
            </button>
            <h1 className="text-sm font-semibold text-foreground">Conversation</h1>
            {chat.liveStatus && (
              <span
                className="hidden items-center gap-1 rounded-full border border-border bg-surface-muted px-2 py-0.5 text-[11px] text-muted sm:inline-flex"
                role="status"
              >
                <Search className="h-3 w-3 animate-pulse" aria-hidden />
                {chat.liveStatus}
              </span>
            )}
          </div>
          <label className="flex max-w-[14rem] cursor-pointer items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
              checked={chat.useDocuments}
              onChange={(e) => chat.setUseDocuments(e.target.checked)}
            />
            <span>
              Answer from documents
              <span className="mt-0.5 block text-[10px] text-muted">Uses uploaded files when on</span>
            </span>
          </label>
        </header>

        <MessageList
          messages={chat.messages}
          isLoading={chat.isLoading}
          liveStatus={chat.liveStatus}
          onPickPrompt={setInput}
          noDocuments={!docs.isLoadingList && docs.documents.length === 0}
          onUploadHint={() => {
            setMobileNav(true);
            docs.openFilePicker();
          }}
        />

        {chat.error && (
          <div className="shrink-0 px-4 pb-2">
            <ErrorBanner
              message={chat.error}
              onRetry={chat.retry}
              onDismiss={chat.dismissError}
              retryDisabled={chat.isLoading}
            />
          </div>
        )}

        <ChatInput
          value={input}
          onChange={setInput}
          onSend={send}
          onStop={chat.stop}
          isLoading={chat.isLoading}
          className="md:rounded-b-2xl"
        />
        </div>
      </div>

      {sidebarCollapsed && (
        <button
          type="button"
          className={cn(
            "fixed bottom-4 left-4 z-20 hidden rounded-xl border border-border bg-surface p-2 md:inline-flex",
          )}
          onClick={() => setSidebarCollapsed(false)}
          aria-label="Show sidebar"
        >
          <Menu className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}