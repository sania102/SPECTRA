export type Depth = "quick" | "standard" | "deep";
export type Level = "high" | "medium" | "low";

export interface EvidenceItem {
  id: string; title: string; url: string | null; source: string; engine: string;
  snippet: string | null; published_at: string | null; date_kind: string | null;
  entity: string | null; claim: string | null; claim_type: string | null; stance: string | null;
  region: string | null; relevance: number; matched_terms: string[];
  source_type: string | null; source_domain: string | null; horizon?: string | null;
}
export interface Signal {
  name: string; surface: string | null; strength: number; confidence: number; level: Level;
  evidence_count: number; trend: string | null; evidence_ids: string[]; rationale: string | null;
}
export interface Divergence {
  id: string; left_signal: string; right_signal: string; magnitude: number; confidence: number;
  explanation: string; higher_signal: string | null; lower_signal: string | null; kind: string;
}
export interface BlindSpot {
  id: string; title: string; description: string; kind: string; importance: number; confidence: number;
  supporting_signals: string[]; evidence_ids: string[]; counter_evidence: string[]; what_could_make_this_wrong: string[];
}
export interface Disagreement {
  id: string; topic: string; kind: string; side_a_label: string; side_b_label: string;
  side_a_evidence_ids: string[]; side_b_evidence_ids: string[]; side_a_sources: number; side_b_sources: number;
  confidence: number; explanation: string;
}
export interface ClaimGroup {
  id: string; label: string; stance: string | null; claim_count: number; source_count: number;
  surfaces: string[]; evidence_ids: string[]; corroborated: boolean;
}
export interface GeoFinding {
  region: string; surface: string; strength: number; evidence_count: number; source_count?: number;
  top_headline: string | null; note: string | null;
}
export interface TrendHorizon { label: string; days: number; change_pct: number | null; direction: string }
export interface TrendSeries {
  query: string; region: string | null; labels: string[]; values: number[]; recent_avg: number; prior_avg: number;
  change_pct: number | null; direction: string; peak_index: number | null;
  window?: string | null; window_label?: string | null; points?: number; span?: string | null;
  window_change_pct?: number | null; window_direction?: string | null; horizons?: TrendHorizon[];
}
export interface DirectionSummary {
  items_up: number; items_down: number; items_neutral: number; directional_items: number; duplicates_collapsed: number;
  long_horizon_excluded: number; unique_sources: number; sources_up: number; sources_down: number; sources_mixed: number;
  surfaces_up: string[]; surfaces_down: string[]; share_up: number | null; lean: string; note: string;
}
export interface RegionSummary {
  region: string; items: number; unique_sources: number; sources_up: number; sources_down: number; lean: string;
  trend_direction: string | null; trend_change_pct: number | null; trend_window: string | null;
  top_headlines: { id: string; title: string; source: string; url: string | null; stance: string | null }[]; evidence_ids: string[];
}
export interface RegionalComparison { regions: RegionSummary[]; agrees: boolean | null; finding: string; caveats: string[] }
export interface ModeProfile {
  label: string; goal: string; trend_window: string; scholar_check: boolean; regional_comparison: boolean; summary: string;
  surface_limit: number; results_per_surface: number; regional_applied: boolean;
}
export interface SurfaceStatus {
  task_id: string; engine: string; surface: string; label: string; query: string;
  status: "completed" | "empty" | "failed"; evidence_count: number; kept_count: number; attempts: number;
  duration_ms: number; region: string | null; error: string | null; error_kind: string | null; rationale: string | null;
}
export interface SearchTask {
  id: string; engine: string; surface: string; query: string; rationale: string; region: string | null;
  params?: Record<string, unknown>; gl?: string | null; max_results?: number;
}
export interface Plan {
  question: string; intent: string; topic: string; depth?: string; configured_surface_limit?: number;
  per_surface_limit?: number; geographic_strategy?: string; geography: string | null; regions: string[];
  is_forecast: boolean; question_horizon?: string; mode_profile?: ModeProfile; time_sensitivity: string; evidence_requirements: string[]; selected_engines: string[];
  search_tasks: SearchTask[]; anchor_terms: string[]; llm_refined: boolean;
}
export interface AnswerLink { title: string; source: string; url: string | null }
export interface AnswerPoint { text: string; evidence_ids: string[]; links: AnswerLink[] }
export interface Answer {
  label: string; tone: "positive" | "negative" | "mixed" | "unknown"; direct_answer: string; confidence: "low" | "medium" | "high";
  confidence_reason: string; evidence_for: AnswerPoint[]; evidence_against: AnswerPoint[]; uncertainty: string[]; next_steps: string[];
  regional_note: string | null;
}
export interface Verdict {
  answer?: Answer | null;
  headline: string; summary: string; lean: string | null; lean_detail: string | null; caveats: string[]; next_steps: string[];
}
export interface DataQuality {
  surfaces_planned: number; surfaces_completed: number; surfaces_failed: number; surfaces_empty: number;
  surfaces_with_evidence?: number; unique_sources?: number; trend_windows?: string[]; reconciled?: boolean;
  tasks_planned?: number; tasks_attempted?: number; tasks_completed?: number; tasks_failed?: number; tasks_empty?: number;
  raw_results: number; kept_results: number; dropped_irrelevant: number; dated_share: number; notes: string[];
}
export interface TemporalContext {
  recent_count: number; prior_count: number; undated_count: number; snapshot_count: number;
  recent_share: number; temporal_coverage: number; direction: string;
}
export interface InvestigationResult {
  investigation_id: string; plan: Plan; signals: Signal[]; divergences: Divergence[]; blind_spots: BlindSpot[];
  disagreements: Disagreement[]; claim_groups: ClaimGroup[]; geo_findings: GeoFinding[]; trend_series: TrendSeries[];
  surface_status: SurfaceStatus[]; verdict: Verdict | null; direction?: DirectionSummary | null; regional?: RegionalComparison | null; data_quality: DataQuality | null; evidence: EvidenceItem[];
  temporal_context: TemporalContext | null; generated_at: string; metadata: Record<string, unknown>;
}

export type StreamEvent =
  | { type: "stage"; stage: string; message: string }
  | { type: "plan"; plan: Plan }
  | { type: "task_start"; task_id: string; engine: string; surface: string; label: string; query: string; region: string | null; rationale: string }
  | { type: "task_done"; task_id: string; engine: string; surface: string; label: string; status: "completed" | "empty" | "failed"; count: number; query: string; attempts: number; duration_ms: number; region: string | null; error?: string | null; error_kind?: string | null }
  | { type: "result"; result: InvestigationResult }
  | { type: "error"; message: string };

export interface RunSummary { id: string; question: string; generated_at: string; blind_spots: number }
