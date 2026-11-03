export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type AlertStatus =
  | "pending"
  | "triaged"
  | "in_review"
  | "escalated"
  | "closed"
  | "suppressed"
  | "false_positive";
export type Verdict = "true_positive" | "suspicious" | "benign" | "false_positive";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
  area: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Asset {
  id: string;
  name: string;
  hostname: string | null;
  ip_address: string | null;
  kind: string;
  criticality: Severity;
  owner_area: string | null;
}

export interface Triage {
  id: string;
  model: string;
  prompt_version: string;
  suggested_severity: Severity;
  verdict: Verdict;
  confidence: number | null;
  summary: string;
  recommended_actions: string[];
  mitre_techniques: string[];
  needs_human_review: boolean;
  human_verdict: Verdict | null;
  reviewed_at: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface Enrichment {
  provider: string;
  indicator: string;
  indicator_type: string;
  verdict: string | null;
  score: number | null;
  raw: Record<string, unknown>;
  fetched_at: string;
}

export interface Alert {
  id: string;
  external_id: string | null;
  title: string;
  description: string | null;
  severity: Severity;
  status: AlertStatus;
  assigned_to: string | null;
  rule_id: string | null;
  rule_level: number | null;
  src_ip: string | null;
  dst_ip: string | null;
  dst_port: number | null;
  protocol: string | null;
  agent_name: string | null;
  dedup_count: number;
  mitre_tactic: string | null;
  mitre_technique: string | null;
  source: string | null;
  asset: Asset | null;
  latest_triage: Triage | null;
  created_at: string;
  first_seen_at: string;
  last_seen_at: string;
}

export interface AlertDetail extends Alert {
  raw_payload: Record<string, unknown>;
  triage_results: Triage[];
  enrichments: Enrichment[];
  incident_code: string | null;
}

export interface AlertPage {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface KpiSet {
  open_alerts: number;
  open_critical: number;
  mttt_minutes: number | null;
  fp_rate_pct: number | null;
  avg_confidence: number | null;
  sla_breached: number;
  auto_triage_pct: number | null;
  mttr_minutes: number | null;
  alerts_today: number;
  alerts_delta_pct: number | null;
}

export interface SeriesPoint {
  label: string;
  value: number;
}

export interface Dashboard {
  kpis: KpiSet;
  daily_volume: SeriesPoint[];
  by_severity: { severity: Severity; count: number }[];
  by_source: SeriesPoint[];
  top_sources_ip: SeriesPoint[];
  aging_buckets: SeriesPoint[];
  sla_compliance_pct: number | null;
  generated_at: string;
}

export interface Incident {
  id: string;
  code: string;
  title: string;
  severity: Severity;
  status: "open" | "investigating" | "contained" | "eradicated" | "recovered" | "closed";
  sla_due_at: string;
  opened_at: string;
  closed_at: string | null;
  resolution: string | null;
  ticket_system: string | null;
  ticket_ref: string | null;
  assigned_to: string | null;
}

export interface Report {
  id: string;
  code: string;
  title: string;
  kind: string;
  format: "pdf" | "docx" | "xlsx";
  period_start: string;
  period_end: string;
  status: string;
  file_size: number | null;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  occurred_at: string;
  user_email: string | null;
  role_code: string | null;
  action: string;
  module: string;
  entity: string | null;
  entity_id: string | null;
  result: "success" | "denied" | "error";
  ip_address: string | null;
  request_id: string | null;
  detail: Record<string, unknown>;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrgUser {
  id: string;
  email: string;
  full_name: string;
  area: string | null;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
  role: { id: number; code: string; name: string; description: string | null };
}

