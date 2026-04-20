interface ScoreBarProps {
  value: number; // 0-1
  label?: string;
  showValue?: boolean;
}

export function ScoreBar({ value, label, showValue = true }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone =
    value >= 0.85 ? "bg-success" : value >= 0.7 ? "bg-primary" : value >= 0.5 ? "bg-warning" : "bg-muted-foreground";
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          {showValue && <span className="font-mono text-foreground/80">{value.toFixed(3)}</span>}
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div className={`h-full rounded-full ${tone} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
