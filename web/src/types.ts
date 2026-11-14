export type Severity = "P1" | "P2" | "P3" | "P4";

export interface TopologyNode {
  id: string;
  name: string;
  type: "CORE" | "TRANSPORT" | "OLT" | "BASE_STATION" | string;
  region: string;
  vendor: string;
}

export interface Topology {
  nodes: TopologyNode[];
  edges: { source: string; target: string; relation: string }[];
}

export interface CaseRecord {
  id: string;
  title: string;
  cause_type: string;
  symptoms: string[];
  root_ne_type: string;
  resolution: string[];
  tags: string[];
}

export interface CaseMatch {
  case: CaseRecord;
  score: number;
}

export interface AlarmCluster {
  id: string;
  root_ne_id: string;
  root_ne_name: string;
  root_ne_type: string;
  cause_type: string;
  cause_label: string;
  confidence: number;
  severity: Severity;
  alarm_count: number;
  affected_node_ids: string[];
  affected_node_names: string[];
  time_start: string;
  time_end: string;
  evidence: string[];
  similar_cases: CaseMatch[];
  plan_steps: string[];
  needs_human_review: boolean;
}

export interface OpsRun {
  id: string;
  created_at: string;
  total_alarms: number;
  cluster_count: number;
  compression_ratio: number;
  overall_severity: Severity;
  clusters: AlarmCluster[];
  summary: string;
  dispatch_plan: string[];
  review_required: boolean;
  topology: Topology;
  llm_mode: string;
}

export interface RunListItem {
  id: string;
  created_at: string;
  total_alarms: number;
  cluster_count: number;
  compression_ratio: number;
  overall_severity: Severity;
}
