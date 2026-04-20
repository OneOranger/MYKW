interface Props {
  text: string;
  highlights: string[];
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function HighlightedText({ text, highlights }: Props) {
  const terms = Array.from(
    new Set(
      highlights
        .map((h) => h.trim())
        .filter((h) => h.length >= 1)
        .sort((a, b) => b.length - a.length)
    )
  );
  if (!terms.length) return <>{text}</>;

  const escaped = terms.map(escapeRegExp);
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(re);
  const lowerSet = new Set(terms.map((t) => t.toLowerCase()));

  return (
    <>
      {parts.map((part, i) => {
        const normalized = part.toLowerCase();
        if (lowerSet.has(normalized)) {
          return (
            <mark key={i} className="hl-mark">
              {part}
            </mark>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
