export type SourceType = "pdf" | "markdown" | "web" | "note" | "slide" | string;

export interface SourceHit {
  id: string;
  rank: number;
  docTitle: string;
  docType: SourceType;
  collection: string;
  author?: string;
  updatedAt: string;
  page?: number;
  section?: string;
  url?: string;
  sourcePath?: string;
  snippet: string;          // raw text of the matched chunk
  highlights: string[];     // tokens to highlight inside snippet
  scores: {
    relevance: number;      // 0-1, final fused score
    vectorSim: number;      // cosine similarity 0-1
    vectorDistance: number; // 0-2 (1 - cosine + jitter)
    rerank: number;         // cross-encoder score 0-1
    bm25: number;           // 0-10
  };
  summary: string;          // AI summary of this chunk
  bullets: string[];        // key points
  entities: { text: string; type: "person" | "org" | "concept" | "tech" | "metric" }[];
  tokens: number;
}

export interface RetrievalMeta {
  totalMs: number;
  embedMs: number;
  searchMs: number;
  rerankMs: number;
  generateMs: number;
  embedModel: string;
  rerankModel: string;
  llmModel: string;
  strategy: "hybrid" | "vector" | "bm25";
  topK: number;
  candidatesScanned: number;
  promptTokens: number;
  completionTokens: number;
  temperature: number;
  fallbackUsed?: boolean;
}

export interface FileMatch {
  title: string;
  sourcePath: string;
  category: string;
  docType: SourceType;
  updatedAt: string;
  chunks: number;
  score: number;
  preview: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  hits?: SourceHit[];
  meta?: RetrievalMeta;
  citationOrder?: string[]; // hit ids in order of citation [1], [2]...
  upgradeDecision?: {
    enabled: boolean;
    candidateId?: string | null;
    status?: string | null;
    message?: string | null;
  } | null;
  canAddToKnowledge?: boolean;
  relatedQuestion?: string;
  answerMode?: "knowledge_qa" | "full_document" | "report" | "file_listing" | string;
  fileMatches?: FileMatch[];
}
