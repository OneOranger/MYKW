import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  Database,
  FolderSync,
  Layers,
  ListChecks,
  RefreshCw,
  Settings2,
  Upload,
  X,
} from "lucide-react";
import { ChatPanel } from "@/components/atlas/ChatPanel";
import { DetailsPanel } from "@/components/atlas/DetailsPanel";
import { ReviewPanel } from "@/components/atlas/ReviewPanel";
import { queryKnowledge } from "@/lib/api";
import {
  createUpgradeCandidate,
  fullSyncRawDocuments,
  getPendingReviews,
  getRuntimeRetrievalConfig,
  getVectorstoreStats,
  previewCandidate,
  recreateVectorstore,
  reviewCandidate,
  reviewCandidatesBatch,
  setRuntimeRetrievalConfig,
  syncRawDocuments,
  uploadKnowledgeFiles,
} from "@/lib/adminApi";
import type { PendingReviewItem } from "@/lib/adminApi";
import type { ChatMessage } from "@/lib/types";

function nowLabel() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

type DetailsMode = "answer" | "review";

const Index = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  const [adminBusy, setAdminBusy] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [runtimeTopK, setRuntimeTopK] = useState(5);
  const [topKInput, setTopKInput] = useState("5");

  const [detailsMode, setDetailsMode] = useState<DetailsMode>("answer");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [pendingItems, setPendingItems] = useState<PendingReviewItem[]>([]);
  const [selectedReviewIds, setSelectedReviewIds] = useState<Set<string>>(new Set());
  const [reviewCategory, setReviewCategory] = useState("all");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewCandidateId, setPreviewCandidateId] = useState<string | null>(null);
  const [previewMarkdown, setPreviewMarkdown] = useState("");

  const [addingMessageId, setAddingMessageId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const sessionId = useMemo(() => `session-${Date.now()}`, []);

  const filteredPendingItems = useMemo(
    () => pendingItems.filter((item) => (reviewCategory === "all" ? true : item.category === reviewCategory)),
    [pendingItems, reviewCategory]
  );

  const pushAssistantNote = (content: string) => {
    const message: ChatMessage = {
      id: `sys-${Date.now()}`,
      role: "assistant",
      content,
      relatedQuestion: "系统消息",
      createdAt: nowLabel(),
      hits: [],
      meta: {
        totalMs: 0,
        embedMs: 0,
        searchMs: 0,
        rerankMs: 0,
        generateMs: 0,
        embedModel: "-",
        rerankModel: "-",
        llmModel: "-",
        strategy: "hybrid",
        topK: 0,
        candidatesScanned: 0,
        promptTokens: 0,
        completionTokens: 0,
        temperature: 0,
      },
      canAddToKnowledge: false,
      answerMode: "knowledge_qa",
      fileMatches: [],
    };
    setMessages((prev) => [...prev, message]);
    setActiveId(message.id);
  };

  const loadRuntimeConfig = async () => {
    try {
      const config = await getRuntimeRetrievalConfig();
      const value = Math.max(1, Number(config.top_k || 5));
      setRuntimeTopK(value);
      setTopKInput(String(value));
    } catch (error) {
      pushAssistantNote(`读取检索参数失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  };

  useEffect(() => {
    void loadRuntimeConfig();
  }, []);

  const loadPendingReviews = async () => {
    setReviewLoading(true);
    try {
      const result = await getPendingReviews();
      setPendingItems(result.items ?? []);
      setSelectedReviewIds(new Set());
      if (previewCandidateId) {
        const exists = (result.items ?? []).some((item) => item.candidate_id === previewCandidateId);
        if (!exists) {
          setPreviewCandidateId(null);
          setPreviewMarkdown("");
        }
      }
      return result.items ?? [];
    } finally {
      setReviewLoading(false);
    }
  };

  const openReviewPanel = async () => {
    setDetailsMode("review");
    try {
      await loadPendingReviews();
    } catch (error) {
      pushAssistantNote(`读取待审核列表失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  };

  const saveRuntimeTopK = async () => {
    const value = Number(topKInput);
    if (!Number.isFinite(value) || value < 1 || value > 50) {
      pushAssistantNote("命中来源数量必须是 1~50 的整数。");
      return;
    }
    setConfigSaving(true);
    try {
      const result = await setRuntimeRetrievalConfig({ top_k: Math.floor(value) });
      setRuntimeTopK(result.top_k);
      setTopKInput(String(result.top_k));
      pushAssistantNote(`已更新命中来源数量上限：${result.top_k}`);
    } catch (error) {
      pushAssistantNote(`保存检索参数失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setConfigSaving(false);
    }
  };

  const send = async (override?: string) => {
    const question = (override ?? input).trim();
    if (!question || loading) return;

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
      createdAt: nowLabel(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await queryKnowledge({
        session_id: sessionId,
        message: question,
        auto_upgrade: false,
        top_k: runtimeTopK,
      });
      const assistantMessage: ChatMessage = {
        id: response.message_id,
        role: "assistant",
        content: response.content,
        createdAt: nowLabel(),
        hits: response.hits ?? [],
        meta: response.meta,
        citationOrder: response.citationOrder,
        upgradeDecision: response.upgradeDecision,
        canAddToKnowledge: !!response.canAddToKnowledge,
        relatedQuestion: question,
        answerMode: response.answerMode,
        fileMatches: response.fileMatches ?? [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setActiveId(assistantMessage.id);
      setDetailsMode("answer");
    } catch (error) {
      pushAssistantNote(
        `请求后端失败：${error instanceof Error ? error.message : "未知错误"}\n请确认后端已启动：http://127.0.0.1:8000`
      );
    } finally {
      setLoading(false);
    }
  };

  const onAddToKnowledge = async (messageId: string) => {
    const target = messages.find((m) => m.id === messageId);
    if (!target || target.role !== "assistant" || !target.canAddToKnowledge || !target.relatedQuestion) return;

    setAddingMessageId(messageId);
    try {
      const result = await createUpgradeCandidate(target.relatedQuestion, target.content);
      const generated = Number(result.generated ?? 0);
      setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, canAddToKnowledge: false } : m)));
      if (generated > 0) {
        pushAssistantNote(`已加入待审核队列，生成 ${generated} 条候选。`);
      } else {
        pushAssistantNote("未生成新候选（可能与已有知识重复）。");
      }
      setDetailsMode("review");
      await loadPendingReviews();
    } catch (error) {
      pushAssistantNote(`加入知识库失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAddingMessageId(null);
    }
  };

  const onUploadClick = () => fileInputRef.current?.click();

  const onUploadSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (!files.length || adminBusy) return;
    setAdminBusy(true);
    try {
      const result = await uploadKnowledgeFiles(files, "general");
      pushAssistantNote(`导入完成：已处理 ${result.files?.length ?? files.length} 个文件。`);
    } catch (error) {
      pushAssistantNote(`导入失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAdminBusy(false);
      event.target.value = "";
    }
  };

  const runSyncRaw = async () => {
    if (adminBusy) return;
    setAdminBusy(true);
    try {
      const result = await syncRawDocuments();
      const changed = Number(result.changed_files ?? 0);
      const indexed = Number(result.indexed_chunks ?? 0);
      if (changed === 0) {
        pushAssistantNote(
          `增量同步完成：changed_files=${changed}, indexed_chunks=${indexed}。\n当前没有检测到新增/变更文件。若你刚审核通过“加入知识库”，请确认该文件已写入 raw/_auto_ingested 后再同步。`
        );
      } else {
        pushAssistantNote(`增量同步完成：changed_files=${changed}, indexed_chunks=${indexed}`);
      }
    } catch (error) {
      pushAssistantNote(`增量同步失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAdminBusy(false);
    }
  };

  const runFullSyncRaw = async () => {
    if (adminBusy) return;
    setAdminBusy(true);
    try {
      const result = await fullSyncRawDocuments();
      pushAssistantNote(
        `全量入库完成：changed_files=${result.changed_files ?? 0}, indexed_chunks=${result.indexed_chunks ?? 0}, total_chunks=${result.total_chunks ?? 0}`
      );
    } catch (error) {
      pushAssistantNote(`全量入库失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAdminBusy(false);
    }
  };

  const runVectorStats = async () => {
    if (adminBusy) return;
    setAdminBusy(true);
    try {
      const result = await getVectorstoreStats();
      pushAssistantNote(`向量状态：table=${result.table_name}, total_rows=${result.total_rows}`);
    } catch (error) {
      pushAssistantNote(`查询向量状态失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAdminBusy(false);
    }
  };

  const runVectorRecreate = async () => {
    if (adminBusy) return;
    setAdminBusy(true);
    try {
      const result = await recreateVectorstore();
      const rebuilt = result.rebuild ?? {};
      pushAssistantNote(
        `重建向量表完成：table=${result.table_name}, total_rows=${result.total_rows}, indexed_files=${rebuilt.indexed_files ?? 0}, indexed_chunks=${rebuilt.indexed_chunks ?? 0}`
      );
    } catch (error) {
      pushAssistantNote(`重建向量表失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setAdminBusy(false);
    }
  };

  const runReviewOne = async (candidateId: string, action: "approve" | "reject") => {
    if (reviewLoading) return;
    setReviewLoading(true);
    try {
      await reviewCandidate(candidateId, action, "UI review");
      await loadPendingReviews();
      setSelectedReviewIds((prev) => {
        const next = new Set(prev);
        next.delete(candidateId);
        return next;
      });
      if (previewCandidateId === candidateId) {
        setPreviewCandidateId(null);
        setPreviewMarkdown("");
      }
      if (action === "approve") {
        pushAssistantNote(
          `审核完成：${candidateId} -> approve。\n已写入 raw/_auto_ingested，请点击“增量同步”完成切分与向量入库。`
        );
      } else {
        pushAssistantNote(`审核完成：${candidateId} -> reject`);
      }
    } catch (error) {
      pushAssistantNote(`审核失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setReviewLoading(false);
    }
  };

  const runBatchReview = async (action: "approve" | "reject") => {
    if (!selectedReviewIds.size || reviewLoading) return;
    setReviewLoading(true);
    try {
      const ids = Array.from(selectedReviewIds);
      const result = await reviewCandidatesBatch(ids, action, "UI batch review");
      if (action === "approve") {
        pushAssistantNote(
          `批量审核完成：成功 ${result.success ?? 0}，失败 ${result.failed ?? 0}。\n已写入 raw/_auto_ingested，请执行一次“增量同步”完成入库。`
        );
      } else {
        pushAssistantNote(`批量审核完成：成功 ${result.success ?? 0}，失败 ${result.failed ?? 0}`);
      }
      await loadPendingReviews();
      setSelectedReviewIds(new Set());
      setPreviewCandidateId(null);
      setPreviewMarkdown("");
    } catch (error) {
      pushAssistantNote(`批量审核失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setReviewLoading(false);
    }
  };

  const runPreview = async (candidateId: string) => {
    setPreviewLoading(true);
    try {
      const result = await previewCandidate(candidateId);
      setPreviewCandidateId(candidateId);
      setPreviewMarkdown(result.markdown ?? "");
    } catch (error) {
      pushAssistantNote(`读取预览失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const toggleSelect = (candidateId: string) => {
    setSelectedReviewIds((prev) => {
      const next = new Set(prev);
      if (next.has(candidateId)) next.delete(candidateId);
      else next.add(candidateId);
      return next;
    });
  };

  const toggleSelectAllFiltered = () => {
    setSelectedReviewIds((prev) => {
      const next = new Set(prev);
      const allSelected =
        filteredPendingItems.length > 0 && filteredPendingItems.every((item) => next.has(item.candidate_id));
      if (allSelected) {
        filteredPendingItems.forEach((item) => next.delete(item.candidate_id));
      } else {
        filteredPendingItems.forEach((item) => next.add(item.candidate_id));
      }
      return next;
    });
  };

  const activeMessage = messages.find((m) => m.id === activeId) ?? null;

  return (
    <>
      <main className="grid h-screen w-full grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_minmax(420px,560px)]">
        <ChatPanel
          messages={messages}
          loading={loading}
          input={input}
          setInput={setInput}
          onSend={send}
          activeMessageId={activeId}
          onSelectMessage={(id) => {
            setActiveId(id);
            setDetailsMode("answer");
          }}
          onAddToKnowledge={onAddToKnowledge}
          addingMessageId={addingMessageId}
          adminOpen={adminOpen}
          onToggleAdmin={() => setAdminOpen((v) => !v)}
        />

        {detailsMode === "review" ? (
          <ReviewPanel
            items={pendingItems}
            loading={reviewLoading}
            previewLoading={previewLoading}
            selectedIds={selectedReviewIds}
            category={reviewCategory}
            previewCandidateId={previewCandidateId}
            previewMarkdown={previewMarkdown}
            onRefresh={loadPendingReviews}
            onCategoryChange={setReviewCategory}
            onToggleSelect={toggleSelect}
            onToggleSelectAllFiltered={toggleSelectAllFiltered}
            onClearSelection={() => setSelectedReviewIds(new Set())}
            onBatchReview={runBatchReview}
            onReviewOne={runReviewOne}
            onPreview={runPreview}
          />
        ) : (
          <DetailsPanel message={activeMessage} />
        )}
      </main>

      <input ref={fileInputRef} type="file" className="hidden" multiple onChange={onUploadSelected} />

      {adminOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setAdminOpen(false)} />
          <aside className="fixed left-0 top-0 z-50 flex h-screen w-[300px] flex-col border-r border-border bg-surface shadow-xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <div className="text-base font-semibold text-foreground">后台管理</div>
                <div className="text-sm text-muted-foreground">知识库维护与检索参数</div>
              </div>
              <button
                onClick={() => setAdminOpen(false)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border hover:bg-primary-soft"
                aria-label="关闭后台面板"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-3 py-3">
              <div className="space-y-2">
                <button
                  onClick={onUploadClick}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-base hover:bg-primary-soft disabled:opacity-50"
                >
                  <Upload className="h-4 w-4 text-primary" />
                  导入文件
                </button>
                <button
                  onClick={runSyncRaw}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-base hover:bg-primary-soft disabled:opacity-50"
                >
                  <FolderSync className="h-4 w-4 text-primary" />
                  增量同步
                </button>
                <button
                  onClick={runFullSyncRaw}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-primary/40 bg-primary-soft px-3 py-2 text-left text-base font-medium text-primary hover:bg-primary/15 disabled:opacity-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  全量入库
                </button>
                <button
                  onClick={runVectorStats}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-base hover:bg-primary-soft disabled:opacity-50"
                >
                  <Database className="h-4 w-4 text-primary" />
                  向量状态
                </button>
                <button
                  onClick={runVectorRecreate}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-base hover:bg-primary-soft disabled:opacity-50"
                >
                  <Layers className="h-4 w-4 text-primary" />
                  重建向量表
                </button>
                <button
                  onClick={openReviewPanel}
                  disabled={adminBusy}
                  className="flex w-full items-center gap-2 rounded-lg border border-primary/40 bg-primary-soft px-3 py-2 text-left text-base font-medium text-primary hover:bg-primary/15 disabled:opacity-50"
                >
                  <ListChecks className="h-4 w-4" />
                  待审核列表
                </button>
              </div>

              <div className="mt-4 rounded-xl border border-border bg-surface-muted/40 p-3">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Settings2 className="h-4 w-4 text-primary" />
                  检索参数
                </div>
                <label className="text-sm text-muted-foreground">右侧命中来源数量（top_k）</label>
                <div className="mt-1.5 flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={topKInput}
                    onChange={(e) => setTopKInput(e.target.value)}
                    className="h-8 w-20 rounded-md border border-border bg-surface px-2 text-base outline-none focus:border-primary/50"
                  />
                  <button
                    onClick={saveRuntimeTopK}
                    disabled={configSaving}
                    className="rounded-md border border-primary/40 bg-primary px-2.5 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
                  >
                    {configSaving ? "保存中..." : "保存"}
                  </button>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">当前生效值：{runtimeTopK}</p>
              </div>
            </div>

            <div className="border-t border-border px-3 py-2 text-sm text-muted-foreground">
              {adminBusy ? "处理中..." : `待审核：${pendingItems.length}`}
            </div>
          </aside>
        </>
      )}
    </>
  );
};

export default Index;
