const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export interface PendingReviewItem {
  candidate_id: string;
  question: string;
  answer: string;
  title: string;
  category: string;
  tags: string[];
  markdown_path: string;
  status: string;
  created_at: string;
}

export async function uploadKnowledgeFiles(files: File[], category = "general") {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  form.append("category", category);
  const resp = await fetch(`${API_BASE}/admin/upload`, { method: "POST", body: form });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function syncRawDocuments() {
  const resp = await fetch(`${API_BASE}/admin/import/sync-raw`, { method: "POST" });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function fullSyncRawDocuments() {
  const resp = await fetch(`${API_BASE}/admin/import/full-sync`, { method: "POST" });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function getVectorstoreStats() {
  const resp = await fetch(`${API_BASE}/admin/vectorstore/stats`);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function getRuntimeRetrievalConfig() {
  const resp = await fetch(`${API_BASE}/admin/runtime/retrieval-config`);
  if (!resp.ok) throw new Error(await resp.text());
  return (await resp.json()) as { ok: boolean; top_k: number };
}

export async function setRuntimeRetrievalConfig(payload: { top_k: number }) {
  const resp = await fetch(`${API_BASE}/admin/runtime/retrieval-config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return (await resp.json()) as { ok: boolean; top_k: number };
}

export async function recreateVectorstore() {
  const resp = await fetch(`${API_BASE}/admin/vectorstore/recreate`, { method: "POST" });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function getPendingReviews(category?: string) {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  const resp = await fetch(`${API_BASE}/admin/upgrade/pending${qs}`);
  if (!resp.ok) throw new Error(await resp.text());
  return (await resp.json()) as { ok: boolean; total: number; items: PendingReviewItem[] };
}

export async function previewCandidate(candidateId: string) {
  const resp = await fetch(`${API_BASE}/admin/upgrade/pending/${candidateId}/preview`);
  if (!resp.ok) throw new Error(await resp.text());
  return (await resp.json()) as { ok: boolean; item: PendingReviewItem; markdown: string };
}

export async function reviewCandidate(candidateId: string, action: "approve" | "reject", note = "") {
  const resp = await fetch(`${API_BASE}/admin/upgrade/review/${candidateId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, reviewer: "ui_user", note }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function reviewCandidatesBatch(
  candidateIds: string[],
  action: "approve" | "reject",
  note = ""
) {
  const resp = await fetch(`${API_BASE}/admin/upgrade/review/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_ids: candidateIds,
      action,
      reviewer: "ui_user",
      note,
    }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function createUpgradeCandidate(question: string, answer: string) {
  const resp = await fetch(`${API_BASE}/upgrade/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, answer }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function revealLocalPath(path: string) {
  const resp = await fetch(`${API_BASE}/admin/files/reveal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
