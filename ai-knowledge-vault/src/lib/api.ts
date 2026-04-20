import type { FileMatch, RetrievalMeta, SourceHit } from "@/lib/types";

export interface QueryApiRequest {
  session_id: string;
  message: string;
  auto_upgrade?: boolean;
  category?: string;
  top_k?: number;
}

export interface QueryApiResponse {
  message_id: string;
  session_id: string;
  role: "assistant";
  content: string;
  createdAt: string;
  hits: SourceHit[];
  meta: RetrievalMeta;
  citationOrder: string[];
  upgradeDecision?: {
    enabled: boolean;
    candidateId?: string | null;
    status?: string | null;
    message?: string | null;
  } | null;
  canAddToKnowledge?: boolean;
  answerMode?: "knowledge_qa" | "full_document" | "report" | "file_listing" | string;
  fileMatches?: FileMatch[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export async function queryKnowledge(payload: QueryApiRequest): Promise<QueryApiResponse> {
  const autoUpgrade = payload.auto_upgrade ?? false;
  const resp = await fetch(`${API_BASE}/query?auto_upgrade=${autoUpgrade ? "true" : "false"}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `请求失败: ${resp.status}`);
  }
  return (await resp.json()) as QueryApiResponse;
}
