import { useState } from "react";
import type { MouseEvent } from "react";
import {
  ExternalLink,
  FileText,
  FileType2,
  FolderSearch,
  Globe,
  Hash,
  Loader2,
  Presentation,
  StickyNote,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { revealLocalPath } from "@/lib/adminApi";
import type { SourceHit } from "@/lib/types";
import { HighlightedText } from "./HighlightedText";
import { ScoreBar } from "./ScoreBar";

const iconFor: Record<string, LucideIcon> = {
  pdf: FileType2,
  markdown: FileText,
  web: Globe,
  note: StickyNote,
  slide: Presentation,
};

const labelFor: Record<string, string> = {
  pdf: "PDF",
  markdown: "Markdown",
  web: "网页",
  note: "笔记",
  slide: "幻灯片",
};

interface Props {
  hit: SourceHit;
  expanded: boolean;
  onToggle: () => void;
}

export function SourceCard({ hit, expanded, onToggle }: Props) {
  const [revealing, setRevealing] = useState(false);

  const docType = (hit.docType || "").toLowerCase();
  const Icon = iconFor[docType] ?? FileText;
  const typeLabel = labelFor[docType] ?? (docType ? docType.toUpperCase() : "文档");

  const handleReveal = async (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (!hit.sourcePath || revealing) return;
    try {
      setRevealing(true);
      await revealLocalPath(hit.sourcePath);
    } finally {
      setRevealing(false);
    }
  };

  return (
    <article className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm transition-all hover:border-primary/30 hover:shadow-md">
      <button onClick={onToggle} className="flex w-full items-start gap-3 p-4 text-left">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <Icon className="h-4 w-4" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-md bg-foreground px-1.5 text-[11px] font-semibold text-background">
              {hit.rank}
            </span>
            <h3 className="truncate text-base font-semibold text-foreground">{hit.docTitle}</h3>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
            <span className="rounded bg-secondary px-1.5 py-0.5 font-medium">{typeLabel}</span>
            <span>·</span>
            <span>{hit.collection}</span>
            {hit.page && (
              <>
                <span>·</span>
                <span className="font-mono">p.{hit.page}</span>
              </>
            )}
            {hit.section && (
              <>
                <span>·</span>
                <span>{hit.section}</span>
              </>
            )}
          </div>
        </div>

        <div className="shrink-0 text-right">
          <div className="font-mono text-base font-semibold text-foreground">
            {(hit.scores.relevance * 100).toFixed(1)}%
          </div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">相关度</div>
        </div>
      </button>

      {expanded && (
        <div className="animate-fade-up border-t border-border bg-surface-muted/40 px-4 pb-4 pt-3">
          <div className="mb-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              <Hash className="h-3 w-3" />
              命中片段
            </div>
            <p className="rounded-lg border border-border bg-surface p-3 text-[15px] leading-relaxed text-foreground/90">
              <HighlightedText text={hit.snippet} highlights={hit.highlights} />
            </p>
          </div>

          <div className="mb-3 grid grid-cols-1 gap-3">
            <div>
              <div className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
                AI 摘要
              </div>
              <p className="text-[15px] leading-relaxed text-foreground/85">{hit.summary}</p>
            </div>
            {hit.bullets.length > 0 && (
              <div>
                <div className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
                  关键要点
                </div>
                <ul className="space-y-1">
                  {hit.bullets.map((b, i) => (
                    <li key={i} className="flex gap-2 text-[15px] text-foreground/85">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {hit.entities.length > 0 && (
            <div className="mb-3">
              <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
                关键实体
              </div>
              <div className="flex flex-wrap gap-1.5">
                {hit.entities.map((e, i) => (
                  <span
                    key={i}
                    className="rounded-md border border-border bg-surface px-2 py-0.5 text-[12px] font-medium text-foreground/80"
                  >
                    {e.text}
                    <span className="ml-1 text-muted-foreground">·{e.type}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mb-3 grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-border bg-surface p-3">
            <ScoreBar value={hit.scores.vectorSim} label="向量相似度 (cosine)" />
            <ScoreBar value={hit.scores.rerank} label="Rerank 分数" />
            <ScoreBar value={hit.scores.relevance} label="融合相关度" />
            <ScoreBar
              value={Math.min(1, hit.scores.bm25 / 10)}
              label={`BM25 (${hit.scores.bm25.toFixed(2)})`}
              showValue={false}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[12px] text-muted-foreground">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>
                作者: <span className="text-foreground/80">{hit.author ?? "-"}</span>
              </span>
              <span>
                更新: <span className="font-mono text-foreground/80">{hit.updatedAt}</span>
              </span>
              <span>
                距离: <span className="font-mono text-foreground/80">{hit.scores.vectorDistance.toFixed(3)}</span>
              </span>
              <span>
                tokens: <span className="font-mono text-foreground/80">{hit.tokens}</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              {hit.sourcePath && (
                <button
                  onClick={handleReveal}
                  disabled={revealing}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-1 text-primary hover:bg-primary-soft disabled:opacity-50"
                >
                  {revealing ? <Loader2 className="h-3 w-3 animate-spin" /> : <FolderSearch className="h-3 w-3" />}
                  在资源管理器定位
                </button>
              )}
              {hit.url && (
                <a
                  href={hit.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  打开原文 <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
