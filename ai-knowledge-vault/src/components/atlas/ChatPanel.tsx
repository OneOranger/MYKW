import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent, ReactNode } from "react";
import { ArrowUp, BookOpen, FolderSearch, Loader2, PanelLeft, Sparkles } from "lucide-react";
import { revealLocalPath } from "@/lib/adminApi";
import type { ChatMessage } from "@/lib/types";
import { sampleQuestions } from "@/lib/mockData";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  input: string;
  setInput: (v: string) => void;
  onSend: (q?: string) => void;
  activeMessageId: string | null;
  onSelectMessage: (id: string) => void;
  onAddToKnowledge: (messageId: string) => void;
  addingMessageId: string | null;
  adminOpen: boolean;
  onToggleAdmin: () => void;
}

function renderContent(text: string, onCite?: (n: number) => void) {
  const lines = text.split("\n");
  return lines.map((line, li) => {
    const parts: ReactNode[] = [];
    const re = /(\*\*[^*]+\*\*|\[\d+\])/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(line)) !== null) {
      if (m.index > last) parts.push(line.slice(last, m.index));
      const token = m[0];
      if (token.startsWith("**")) {
        parts.push(
          <strong key={`${li}-${m.index}`} className="font-semibold text-foreground">
            {token.slice(2, -2)}
          </strong>
        );
      } else {
        const n = Number(token.slice(1, -1));
        parts.push(
          <button
            key={`${li}-${m.index}`}
            onClick={() => onCite?.(n)}
            className="mx-0.5 inline-flex h-[20px] min-w-[20px] items-center justify-center rounded-md bg-primary-soft px-1 align-baseline font-mono text-[11px] font-semibold text-primary hover:bg-primary hover:text-primary-foreground"
          >
            {n}
          </button>
        );
      }
      last = m.index + token.length;
    }
    if (last < line.length) parts.push(line.slice(last));
    return (
      <p key={li} className={li === 0 ? "" : "mt-2"}>
        {parts.length ? parts : line || "\u00A0"}
      </p>
    );
  });
}

export function ChatPanel({
  messages,
  loading,
  input,
  setInput,
  onSend,
  activeMessageId,
  onSelectMessage,
  onAddToKnowledge,
  addingMessageId,
  adminOpen,
  onToggleAdmin,
}: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [revealingPath, setRevealingPath] = useState<string | null>(null);

  const hasAnyMessage = messages.length > 0;
  const hasAssistant = useMemo(() => messages.some((m) => m.role === "assistant"), [messages]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const handleKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const handleRevealPath = async (path: string, event: MouseEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!path || revealingPath) return;
    try {
      setRevealingPath(path);
      await revealLocalPath(path);
    } finally {
      setRevealingPath(null);
    }
  };

  return (
    <section className="flex h-full min-h-0 flex-col bg-gradient-subtle text-[17px]">
      <header className="flex shrink-0 items-center justify-between border-b border-border bg-surface/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-primary text-primary-foreground shadow-sm">
            <BookOpen className="h-4.5 w-4.5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-foreground">Atlas</h1>
            <p className="text-sm text-muted-foreground">个人 AI 知识库问答</p>
          </div>
          <button
            type="button"
            onClick={onToggleAdmin}
            className={`ml-2 inline-flex h-10 w-10 items-center justify-center rounded-xl border transition ${
              adminOpen
                ? "border-primary/50 bg-primary-soft text-primary"
                : "border-border bg-surface text-muted-foreground hover:border-primary/40 hover:text-foreground"
            }`}
            aria-label={adminOpen ? "隐藏后台管理" : "展开后台管理"}
            title={adminOpen ? "隐藏后台管理" : "展开后台管理"}
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        </div>

        <div className="hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-sm text-muted-foreground sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          检索引擎在线
        </div>
      </header>

      <div ref={viewportRef} className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-3xl">
          {!hasAnyMessage && !loading && (
            <div className="rounded-2xl border border-dashed border-border bg-surface/50 p-8 text-center">
              <Sparkles className="mx-auto mb-3 h-8 w-8 text-primary" />
              <h2 className="text-xl font-semibold text-foreground">向你的知识库提问</h2>
              <p className="mt-1 text-base text-muted-foreground">系统会返回答案，并展示来源与检索详情。</p>
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {sampleQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => onSend(q)}
                    className="rounded-lg border border-border bg-surface px-3 py-2 text-left text-sm text-foreground/80 transition-colors hover:border-primary/40 hover:bg-primary-soft"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {messages.map((message) => {
              if (message.role === "user") {
                return (
                  <div key={message.id} className="flex justify-end animate-fade-up">
                    <div className="max-w-[86%] rounded-2xl rounded-tr-sm bg-foreground px-4 py-3 text-base text-background shadow-sm">
                      {message.content}
                    </div>
                  </div>
                );
              }

              const isActive = activeMessageId === message.id;

              return (
                <div key={message.id} className="flex justify-start animate-fade-up">
                  <div
                    className={`max-w-[92%] rounded-2xl rounded-tl-sm border bg-surface px-4 py-3 text-base text-foreground/90 shadow-sm transition-all ${
                      isActive ? "border-primary/40 ring-2 ring-primary/10" : "border-border hover:border-primary/30"
                    }`}
                    onClick={() => onSelectMessage(message.id)}
                  >
                    <div className="leading-relaxed">{renderContent(message.content)}</div>

                    {!!message.fileMatches?.length && (
                      <div className="mt-3 rounded-lg border border-primary/20 bg-primary-soft/50 p-3">
                        <div className="mb-2 text-sm font-semibold text-foreground">
                          相关文件（可直接定位到资源管理器）
                        </div>
                        <div className="max-h-52 space-y-2 overflow-y-auto pr-1">
                          {message.fileMatches.map((file, index) => (
                            <button
                              key={`${file.sourcePath}-${index}`}
                              onClick={(event) => handleRevealPath(file.sourcePath, event)}
                              disabled={revealingPath === file.sourcePath}
                              className="flex w-full items-start justify-between gap-2 rounded-md border border-border bg-surface px-3 py-2 text-left text-sm hover:border-primary/40 hover:bg-primary-soft disabled:opacity-60"
                            >
                              <div className="min-w-0 flex-1">
                                <div className="truncate font-medium text-foreground">{file.title}</div>
                                <div className="mt-0.5 truncate text-xs text-muted-foreground">
                                  {file.docType} · {file.category} · {file.chunks} chunks
                                </div>
                              </div>
                              <span className="mt-0.5 inline-flex items-center gap-1 text-xs text-primary">
                                {revealingPath === file.sourcePath ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <FolderSearch className="h-3.5 w-3.5" />
                                )}
                                定位
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {message.canAddToKnowledge && (
                      <div className="mt-3 border-t border-border pt-2.5">
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            onAddToKnowledge(message.id);
                          }}
                          disabled={addingMessageId === message.id}
                          className="inline-flex items-center gap-1 rounded-md border border-primary/40 bg-primary px-2.5 py-1.5 text-sm font-medium text-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-60"
                        >
                          {addingMessageId === message.id ? (
                            <>
                              <Loader2 className="h-3 w-3 animate-spin" />
                              加入中...
                            </>
                          ) : (
                            "加入知识库"
                          )}
                        </button>
                      </div>
                    )}

                    <div className="mt-3 flex items-center gap-2 border-t border-border pt-2.5 text-sm text-muted-foreground">
                      {message.hits && message.hits.length > 0 ? (
                        <>
                          <span className="font-medium text-foreground/70">{message.hits.length} 条来源</span>
                          <span>·</span>
                        </>
                      ) : (
                        <>
                          <span className="font-medium text-foreground/70">模型回答</span>
                          <span>·</span>
                        </>
                      )}
                      <span className="font-mono">{message.meta?.totalMs ?? 0}ms</span>
                      <span>·</span>
                      <span>{message.meta?.completionTokens ?? 0} tokens</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {loading && (
            <div className="mt-3 flex animate-fade-up justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">{hasAssistant ? "检索中..." : "思考中..."}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-border bg-surface/80 px-6 py-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-sm focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/15">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="向知识库提问，例如：给我显示征信报告 PDF 的全部内容，并进行总结"
              className="scrollbar-thin max-h-40 flex-1 resize-none bg-transparent px-2 py-2 text-base text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
            <button
              onClick={() => onSend()}
              disabled={!input.trim() || loading}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-primary text-primary-foreground shadow-sm transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="发送"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-sm text-muted-foreground">Enter 发送 · Shift + Enter 换行</p>
        </div>
      </div>
    </section>
  );
}
