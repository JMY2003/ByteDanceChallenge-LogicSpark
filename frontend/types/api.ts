export type ProjectCreated = {
  project_id: string;
  status: string;
};

export type ProjectStatus = {
  project_id: string;
  status: string;
  query: string;
  mode: string;
  language: string;
  task_counts: Record<string, number>;
  current_nodes: string[];
  quality_score?: QualityScore | null;
};

export type ProjectHistoryItem = {
  project_id: string;
  status: string;
  query: string;
  mode: string;
  language: string;
  created_at: string;
  completed_at: string;
  task_counts: Record<string, number>;
  quality_score?: QualityScore | null;
};

export type DagNode = {
  id: string;
  label: string;
  agent_name: string;
  depends_on: string[];
  status: string;
  retry_count: number;
  max_retries: number;
  human_review_required: boolean;
};

export type DagEdge = {
  id: string;
  source: string;
  target: string;
};

export type DagResponse = {
  project_id: string;
  nodes: DagNode[];
  edges: DagEdge[];
};

export type AgentRun = {
  id: string;
  project_id: string;
  task_id: string;
  agent_name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  tool_calls: Array<Record<string, unknown>>;
  model: string;
  token_usage: Record<string, number>;
  cost_estimate?: number | null;
  error?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms: number;
};

export type CompetitorProfile = {
  competitor_id: string;
  name: string;
  website?: string | null;
  product_category: string;
  target_users: string[];
  business_model: string[];
  positioning: {
    short_summary?: string;
    long_summary?: string;
    evidence_ids?: string[];
  };
  features: Array<{
    feature_id: string;
    name: string;
    category: string;
    support_status: string;
    maturity: string;
    evidence_ids: string[];
  }>;
  pricing: Array<{
    plan_name: string;
    price: string;
    billing_cycle: string;
    evidence_ids: string[];
  }>;
  user_feedback: {
    pros: Array<Record<string, unknown>>;
    cons: Array<Record<string, unknown>>;
  };
  technical_signals: Array<Record<string, unknown>>;
  swot?: {
    strengths?: Array<{ point?: string; confidence?: number; evidence_ids?: string[] }>;
    weaknesses?: Array<{ point?: string; confidence?: number; evidence_ids?: string[] }>;
    opportunities?: Array<{ point?: string; confidence?: number; evidence_ids?: string[] }>;
    threats?: Array<{ point?: string; confidence?: number; evidence_ids?: string[] }>;
  };
  source_coverage?: string[];
  last_updated: string;
};

export type EvidenceItem = {
  evidence_id: string;
  source_url: string;
  source_title: string;
  source_type: string;
  publisher?: string | null;
  retrieved_at: string;
  doc_id?: string | null;
  chunk_id?: string | null;
  quote: string;
  summary: string;
  credibility_score: number;
  freshness_score: number;
  is_primary_source: boolean;
  is_potentially_outdated: boolean;
  supports_claim_ids: string[];
  metadata: Record<string, unknown>;
};

export type QualityScore = {
  total: number;
  coverage: number;
  evidence_strength: number;
  citation_accuracy: number;
  analysis_depth: number;
  structure: number;
  consistency: number;
  readability: number;
  novelty: number;
};

export type ReportResponse = {
  project_id: string;
  markdown?: string | null;
  html?: string | null;
  json_report?: Record<string, unknown> | null;
  quality_score?: QualityScore | null;
};
