import { Activity, Cpu, Search, Sparkles, Timer } from "lucide-react";
import type { ReactNode } from "react";
import type { RetrievalMeta } from "@/lib/types";

interface Props {
  meta: RetrievalMeta;
}

const stageColor: Record<string, string> = {
  embed: "bg-primary",
  search: "bg-success",
  rerank: "bg-warning",
  generate: "bg-foreground",
};

export function RetrievalMetaPanel({ meta }: Props) {
  const stages = [
    { key: "embed", label: "嵌入", ms: meta.embedMs },
    { key: "search", label: "检索", ms: meta.searchMs },
    { key: "rerank", label: "重排", ms: meta.rerankMs },
    { key: "generate", label: "生成", ms: meta.generateMs },
  ];
  const total = Math.max(1, stages.reduce((sum, s) => sum + s.ms, 0));

  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">检索元数据</h3>
        </div>
        <div className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
          <Timer className="h-3 w-3" /> {meta.totalMs} ms
        </div>
      </div>

      <div className="mb-3">
        <div className="flex h-2 w-full overflow-hidden rounded-full bg-secondary">
          {stages.map((s) => (
            <div
              key={s.key}
              className={stageColor[s.key]}
              style={{ width: `${(s.ms / total) * 100}%` }}
              title={`${s.label}: ${s.ms}ms`}
            />
          ))}
        </div>
        <div className="mt-2 grid grid-cols-4 gap-2 text-[11px]">
          {stages.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${stageColor[s.key]}`} />
              <span className="text-muted-foreground">{s.label}</span>
              <span className="ml-auto font-mono text-foreground/80">{s.ms}ms</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2 rounded-lg border border-border bg-surface-muted/50 p-3 text-xs">
        <Row icon={<Sparkles className="h-3 w-3" />} label="LLM" value={meta.llmModel} />
        <Row icon={<Cpu className="h-3 w-3" />} label="Embedding" value={meta.embedModel} />
        <Row icon={<Search className="h-3 w-3" />} label="Reranker" value={meta.rerankModel} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <Stat label="检索策略" value={meta.strategy.toUpperCase()} />
        <Stat label="Top-K" value={String(meta.topK)} />
        <Stat label="候选扫描" value={meta.candidatesScanned.toLocaleString()} />
        <Stat label="温度" value={meta.temperature.toFixed(2)} />
        <Stat label="Prompt tokens" value={meta.promptTokens.toLocaleString()} />
        <Stat label="Completion tokens" value={meta.completionTokens.toLocaleString()} />
      </div>
    </div>
  );
}

function Row({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="flex items-center gap-1.5 text-muted-foreground">
        {icon}
        {label}
      </span>
      <span className="truncate font-mono text-foreground/85">{value}</span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-mono text-sm text-foreground">{value}</div>
    </div>
  );
}
