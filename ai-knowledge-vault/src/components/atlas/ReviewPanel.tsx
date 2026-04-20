import { CheckCheck, Eye, FileText, Filter, Inbox, Loader2, RefreshCw, XCircle } from "lucide-react";
import type { PendingReviewItem } from "@/lib/adminApi";

interface Props {
  items: PendingReviewItem[];
  loading: boolean;
  previewLoading: boolean;
  selectedIds: Set<string>;
  category: string;
  previewCandidateId: string | null;
  previewMarkdown: string;
  onRefresh: () => void;
  onCategoryChange: (value: string) => void;
  onToggleSelect: (candidateId: string) => void;
  onToggleSelectAllFiltered: () => void;
  onClearSelection: () => void;
  onBatchReview: (action: "approve" | "reject") => void;
  onReviewOne: (candidateId: string, action: "approve" | "reject") => void;
  onPreview: (candidateId: string) => void;
}

export function ReviewPanel({
  items,
  loading,
  previewLoading,
  selectedIds,
  category,
  previewCandidateId,
  previewMarkdown,
  onRefresh,
  onCategoryChange,
  onToggleSelect,
  onToggleSelectAllFiltered,
  onClearSelection,
  onBatchReview,
  onReviewOne,
  onPreview,
}: Props) {
  const categories = Array.from(new Set(items.map((item) => item.category || "general"))).sort();
  const filteredItems = items.filter((item) => (category === "all" ? true : item.category === category));
  const allFilteredSelected =
    filteredItems.length > 0 && filteredItems.every((item) => selectedIds.has(item.candidate_id));

  return (
    <aside className="flex h-full min-h-0 flex-col border-l border-border bg-surface-muted/40">
      <div className="shrink-0 border-b border-border bg-surface/80 px-5 py-3 backdrop-blur">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">待审核列表</h2>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-primary-soft disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            刷新
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-1 text-xs">
            <Filter className="h-3 w-3 text-muted-foreground" />
            <select
              value={category}
              onChange={(e) => onCategoryChange(e.target.value)}
              className="bg-transparent text-foreground outline-none"
            >
              <option value="all">全部分类</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={onToggleSelectAllFiltered}
            disabled={!filteredItems.length}
            className="rounded-md border border-border px-2 py-1 text-xs hover:bg-primary-soft disabled:opacity-50"
          >
            {allFilteredSelected ? "取消全选" : "全选当前筛选"}
          </button>

          <button
            onClick={onClearSelection}
            disabled={!selectedIds.size}
            className="rounded-md border border-border px-2 py-1 text-xs hover:bg-primary-soft disabled:opacity-50"
          >
            清空选择
          </button>

          <button
            onClick={() => onBatchReview("approve")}
            disabled={!selectedIds.size || loading}
            className="inline-flex items-center gap-1 rounded-md border border-success/40 bg-success/10 px-2 py-1 text-xs text-success hover:bg-success/15 disabled:opacity-50"
          >
            <CheckCheck className="h-3 w-3" />
            批量通过
          </button>

          <button
            onClick={() => onBatchReview("reject")}
            disabled={!selectedIds.size || loading}
            className="inline-flex items-center gap-1 rounded-md border border-destructive/40 bg-destructive/10 px-2 py-1 text-xs text-destructive hover:bg-destructive/15 disabled:opacity-50"
          >
            <XCircle className="h-3 w-3" />
            批量拒绝
          </button>
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-4">
        {!filteredItems.length ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <Inbox className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">当前筛选下没有待审核数据</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
            <table className="w-full table-fixed text-xs">
              <thead className="bg-surface-muted/70">
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="w-10 px-2 py-2">
                    <input
                      type="checkbox"
                      checked={allFilteredSelected}
                      onChange={onToggleSelectAllFiltered}
                      className="h-3.5 w-3.5 rounded border-border"
                    />
                  </th>
                  <th className="w-[34%] px-2 py-2">标题</th>
                  <th className="w-[18%] px-2 py-2">分类</th>
                  <th className="w-[16%] px-2 py-2">创建时间</th>
                  <th className="w-[32%] px-2 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.candidate_id} className="border-b border-border/70 align-top">
                    <td className="px-2 py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(item.candidate_id)}
                        onChange={() => onToggleSelect(item.candidate_id)}
                        className="h-3.5 w-3.5 rounded border-border"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <div className="line-clamp-2 font-medium text-foreground">{item.title}</div>
                      <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
                        {item.candidate_id}
                      </div>
                    </td>
                    <td className="px-2 py-2 text-foreground/90">{item.category || "general"}</td>
                    <td className="px-2 py-2 text-muted-foreground">{item.created_at?.slice(0, 10)}</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-1">
                        <button
                          onClick={() => onPreview(item.candidate_id)}
                          disabled={previewLoading}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] hover:bg-primary-soft disabled:opacity-50"
                        >
                          <Eye className="h-3 w-3" />
                          预览
                        </button>
                        <button
                          onClick={() => onReviewOne(item.candidate_id, "approve")}
                          disabled={loading}
                          className="rounded-md border border-success/40 bg-success/10 px-2 py-1 text-[11px] text-success hover:bg-success/15 disabled:opacity-50"
                        >
                          通过
                        </button>
                        <button
                          onClick={() => onReviewOne(item.candidate_id, "reject")}
                          disabled={loading}
                          className="rounded-md border border-destructive/40 bg-destructive/10 px-2 py-1 text-[11px] text-destructive hover:bg-destructive/15 disabled:opacity-50"
                        >
                          拒绝
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 rounded-xl border border-border bg-surface p-3 shadow-sm">
          <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            Markdown 预览
            {previewCandidateId && <span className="font-mono text-foreground/80">{previewCandidateId}</span>}
          </div>
          {previewLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              加载预览中...
            </div>
          ) : previewMarkdown ? (
            <pre className="scrollbar-thin max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-muted/40 p-3 text-[12px] leading-relaxed text-foreground/90">
              {previewMarkdown}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">点击上方“预览”查看候选 Markdown。</p>
          )}
        </div>
      </div>
    </aside>
  );
}
