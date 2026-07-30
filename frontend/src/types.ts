export type Role = "ADMIN" | "ANALYST" | "REVIEWER";

export type DocumentStatus =
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "NEEDS_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "FAILED";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
}

export interface Session {
  token: string;
  user: User;
}

export interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
  confidence: number;
}

export interface RiskFlag {
  severity: "LOW" | "MEDIUM" | "HIGH" | string;
  code: string;
  message: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  status: DocumentStatus;
  category: string | null;
  language: string | null;
  pageCount: number;
  confidence: number | null;
  tags: string[];
  createdByName: string;
  createdAt: string;
  updatedAt: string;
}

export interface Job {
  id: string;
  documentId: string;
  documentTitle: string;
  status: string;
  currentStage: string;
  progress: number;
  attempt: number;
  maxRetries: number;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface Review {
  id: string;
  documentId: string;
  documentTitle: string;
  category: string | null;
  confidence: number | null;
  status: "PENDING" | "APPROVED" | "REJECTED";
  assignedToName: string | null;
  notes: string | null;
  corrections: Record<string, unknown>;
  riskFlags: RiskFlag[];
  createdAt: string;
  decidedAt: string | null;
}

export interface JobEvent {
  id: string;
  stage: string;
  level: string;
  message: string;
  progress: number;
  created_at?: string;
  createdAt?: string;
}

export interface DocumentDetail extends DocumentItem {
  sha256: string;
  rawText: string;
  redactedText: string;
  summary: string;
  keywords: string[];
  entities: Entity[];
  fields: Record<string, unknown>;
  riskFlags: RiskFlag[];
  job: Job | null;
  review: Review | null;
  chunks: Array<{
    id: string;
    position: number;
    text: string;
    token_estimate: number;
  }>;
  events: JobEvent[];
}

export interface Dashboard {
  metrics: {
    totalDocuments: number;
    readyDocuments: number;
    pendingReview: number;
    activeJobs: number;
    averageConfidence: number;
  };
  categoryDistribution: Array<{ category: string; count: number }>;
  recentDocuments: DocumentItem[];
  activeJobs: Job[];
  reviewQueue: Review[];
  generatedAt: string;
}

export interface SearchResult {
  documentId: string;
  title: string;
  category: string | null;
  status: DocumentStatus;
  snippet: string;
  rank: number;
  updatedAt: string;
}

export interface ExtractionTemplate {
  id: string;
  name: string;
  documentType: string;
  description: string;
  fields: Array<{
    key: string;
    label: string;
    required: boolean;
  }>;
  active: boolean;
  createdAt: string;
}

export interface AuditEvent {
  id: string;
  actorName: string | null;
  actorEmail: string | null;
  action: string;
  entityType: string;
  entityId: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}
