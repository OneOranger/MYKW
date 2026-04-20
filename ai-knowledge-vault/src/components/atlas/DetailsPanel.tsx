import { useState } from "react";
import type { ComponentType } from "react";
import { FileSearch, Inbox, Sparkles } from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { RetrievalMetaPanel } from "./RetrievalMetaPanel";
import { SourceCard } from "./SourceCard";

interface Props {
  message: ChatMessage | null;
}

type Tab = "sources" | "meta" | "synthesis";

export function DetailsPanel({ message }: Props) {
  const [tab, setTab] = useState<Tab>("sources");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const hits = message?.hits ?? [];
  const avgRelevance = hits.length ? hits.reduce((sum, h) => sum + h.scores.relevance, 0) / hits.length : 0;
  const topScore = hits.length ? Math.max(...hits.map((h) => h.scores.relevance)) : 0;

  const tabs: { key: Tab; label: string; icon: ComponentType<{ className?: string }>; count?: number }[] = [
    { key: "sources", label: "命中来源", icon: FileSearch, count: hits.length },
    { key: "synthesis", label: "综合摘要", icon: Sparkles },
    { key: "meta", label: "检索元数据", icon: Inbox },
  ];

  if (!message || !message.meta) {
    return (
      <aside className="flex h-full min-h-0 items-center justify-center border-l border-border bg-surface-muted/30 p-8">
        <div className="text-center">
          <Inbox className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
          <h3 className="text-base font-semibold text-foreground">回答详情</h3>
          <p className="mt-1 max-w-xs text-sm text-muted-foreground">
            选择左侧任意一条回答，这里会显示命中来源、片段高亮与检索过程。
          </p>
        </div>
      </aside>
    );
  }

  const entityMap = new Map<string, { type: string; count: number }>();
  hits.forEach((h) => {
    h.entities.forEach((e) => {
      const prev = entityMap.get(e.text);
      entityMap.set(e.text, { type: e.type, count: (prev?.count ?? 0) + 1 });
    });
  });
  const topEntities = Array.from(entityMap.entries())
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 8);

  return (
    <aside className="flex h-full min-h-0 flex-col border-l border-border bg-surface-muted/40 text-[16px]">
      <div className="shrink-0 border-b border-border bg-surface/80 px-5 py-3 backdrop-blur">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground">回答详情</h2>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>
              均分 <span className="font-mono text-foreground/80">{(avgRelevance * 100).toFixed(1)}%</span>
            </span>
            <span>
              峰值 <span className="font-mono text-success">{(topScore * 100).toFixed(1)}%</span>
            </span>
          </div>
        </div>

        <div className="mt-3 flex gap-1 rounded-lg bg-secondary p-1">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
                  active ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
                {t.count !== undefined && (
                  <span className="ml-0.5 rounded bg-foreground/10 px-1 font-mono text-[11px]">{t.count}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-4">
        {tab === "sources" && (
          <>
            {!hits.length ? (
              <div className="rounded-xl border border-border bg-surface p-6 text-center">
                <p className="text-base text-muted-foreground">
                  当前问题没有命中可靠知识片段，本次回答由模型通用能力生成。
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {hits.map((h) => (
                  <SourceCard
                    key={h.id}
                    hit={h}
                    expanded={expanded[h.id] ?? h.rank === 1}
                    onToggle={() =>
                      setExpanded((state) => ({ ...state, [h.id]: !(state[h.id] ?? h.rank === 1) }))
                    }
                  />
                ))}
              </div>
            )}
          </>
        )}

        {tab === "meta" && <RetrievalMetaPanel meta={message.meta} />}

        {tab === "synthesis" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
              <div className="mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h3 className="text-base font-semibold text-foreground">综合要点</h3>
              </div>
              {!hits.length ? (
                <p className="text-base text-muted-foreground">没有可汇总的本地命中片段。</p>
              ) : (
                <ul className="space-y-2">
                  {hits
                    .flatMap((h) => h.bullets.map((b) => ({ b, rank: h.rank })))
                    .slice(0, 8)
                    .map((row, i) => (
                      <li key={i} className="flex gap-2 text-base leading-relaxed text-foreground/85">
                        <span className="mt-0.5 flex h-5 min-w-[18px] items-center justify-center rounded bg-primary-soft px-1 font-mono text-[11px] font-semibold text-primary">
                          {row.rank}
                        </span>
                        {row.b}
                      </li>
                    ))}
                </ul>
              )}
            </div>

            {!!topEntities.length && (
              <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
                <h3 className="mb-2 text-base font-semibold text-foreground">高频实体</h3>
                <div className="flex flex-wrap gap-1.5">
                  {topEntities.map(([name, info]) => (
                    <span
                      key={name}
                      className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-muted/50 px-2 py-1 text-sm"
                    >
                      <span className="font-medium text-foreground">{name}</span>
                      <span className="text-muted-foreground">·{info.type}</span>
                      <span className="rounded bg-foreground/10 px-1 font-mono text-[11px] text-foreground/70">
                        ×{info.count}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
