from datetime import datetime
from pydantic import BaseModel, Field
from .search import InvestigationIntent, SearchTask


class EvidenceItem(BaseModel):
    id: str
    title: str
    url: str | None = None
    source: str
    engine: str
    snippet: str | None = None
    published_at: datetime | None = None
    # "published" = the source stated a date; "observed" = live snapshot (e.g. a
    # shopping listing seen now). None = no usable date was available.
    date_kind: str | None = None
    entity: str | None = None
    claim: str | None = None
    claim_type: str | None = None
    stance: str | None = None  # "up" | "down" | "mixed" | "neutral" | None
    location: str | None = None
    region: str | None = None
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_domain: str | None = None
    source_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    retrieval_rank: int | None = Field(default=None, ge=1)
    # Time horizon the item talks about: "near" (the period asked about), "long"
    # (a different, longer period such as "by 2030") or None (unspecified).
    horizon: str | None = None


class TrendHorizon(BaseModel):
    label: str          # e.g. "last 30 days vs the 30 days before"
    days: int
    change_pct: float | None = None
    direction: str = "flat"


class TrendSeries(BaseModel):
    query: str
    region: str | None = None
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    timestamps: list[int] = Field(default_factory=list)
    recent_avg: float = 0.0
    prior_avg: float = 0.0
    # change_pct / direction use the SAME yardstick in every mode (last 30 days vs
    # the 30 days before) so Quick, Standard and Deep are comparable.
    change_pct: float | None = None
    direction: str = "flat"  # rising | falling | flat
    peak_index: int | None = None
    # Requested vs actually returned window (verifies the plan was executed).
    window: str | None = None          # SerpApi value, e.g. "today 3-m"
    window_label: str | None = None    # "past 3 months"
    points: int = 0
    span: str | None = None            # "Jul 13 2026 → Oct 4 2026"
    window_change_pct: float | None = None   # change inside the requested window (recent 15% vs prior 15%)
    window_direction: str | None = None
    horizons: list[TrendHorizon] = Field(default_factory=list)


class Signal(BaseModel):
    name: str
    surface: str | None = None
    strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    level: str = "low"  # high | medium | low
    evidence_count: int = 0
    trend: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None


class Divergence(BaseModel):
    id: str
    left_signal: str
    right_signal: str
    magnitude: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    higher_signal: str | None = None
    lower_signal: str | None = None
    kind: str = "level"  # level | momentum


class BlindSpot(BaseModel):
    id: str
    title: str
    description: str
    kind: str = "divergence"  # divergence | coverage | temporal | disagreement | forecast
    importance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_signals: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    what_could_make_this_wrong: list[str] = Field(default_factory=list)


class Disagreement(BaseModel):
    id: str
    topic: str
    kind: str  # within_surface | across_surfaces
    side_a_label: str
    side_b_label: str
    side_a_evidence_ids: list[str] = Field(default_factory=list)
    side_b_evidence_ids: list[str] = Field(default_factory=list)
    side_a_sources: int = 0
    side_b_sources: int = 0
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str


class ClaimGroup(BaseModel):
    id: str
    label: str
    stance: str | None = None
    claim_count: int
    source_count: int
    surfaces: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    corroborated: bool = False


class GeoFinding(BaseModel):
    region: str
    surface: str
    strength: float = Field(ge=0.0, le=1.0)
    evidence_count: int
    source_count: int = 0
    top_headline: str | None = None
    note: str | None = None


class SurfaceStatus(BaseModel):
    task_id: str
    engine: str
    surface: str
    label: str
    query: str
    status: str  # completed | empty | failed
    evidence_count: int = 0
    kept_count: int = 0
    attempts: int = 1
    duration_ms: int = 0
    region: str | None = None
    error: str | None = None
    error_kind: str | None = None
    rationale: str | None = None


class InvestigationPlan(BaseModel):
    question: str
    intent: InvestigationIntent
    topic: str
    depth: str = "standard"
    configured_surface_limit: int = 5
    per_surface_limit: int = 10
    geographic_strategy: str = "global_overview"
    question_horizon: str = "unspecified"   # near | unspecified
    mode_profile: dict = Field(default_factory=dict)
    geography: str | None = None
    regions: list[str] = Field(default_factory=list)
    is_forecast: bool = False
    time_sensitivity: str
    evidence_requirements: list[str] = Field(default_factory=list)
    selected_engines: list[str] = Field(default_factory=list)
    search_tasks: list[SearchTask] = Field(default_factory=list)
    anchor_terms: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    llm_refined: bool = False


class EntityProfile(BaseModel):
    canonical: str
    mentions: int = Field(ge=0)
    evidence_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class TemporalContext(BaseModel):
    recent_count: int = Field(ge=0)
    prior_count: int = Field(ge=0)
    undated_count: int = Field(ge=0)
    snapshot_count: int = 0
    recent_share: float = Field(ge=0.0, le=1.0)
    temporal_coverage: float = Field(ge=0.0, le=1.0)
    direction: str


class ContextCoverage(BaseModel):
    geography: str | None = None
    matched_count: int = Field(ge=0)
    unspecified_count: int = Field(ge=0)
    mismatch_count: int = Field(ge=0)
    context_coverage: float = Field(ge=0.0, le=1.0)


class CrossSurfaceFinding(BaseModel):
    id: str
    finding_type: str
    title: str
    description: str
    signal_names: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class AnswerLink(BaseModel):
    title: str
    source: str = ""
    url: str | None = None


class AnswerPoint(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    links: list[AnswerLink] = Field(default_factory=list)


class Answer(BaseModel):
    """A direct, honest answer to the user's question, with the evidence behind it."""
    label: str                 # e.g. "Not yet", "Leans up", "Mixed"
    tone: str = "unknown"      # positive | negative | mixed | unknown
    direct_answer: str
    confidence: str = "low"    # low | medium | high  (confidence in the evidence, not in a real-world outcome)
    confidence_reason: str = ""
    evidence_for: list[AnswerPoint] = Field(default_factory=list)
    evidence_against: list[AnswerPoint] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    regional_note: str | None = None


class Verdict(BaseModel):
    answer: Answer | None = None
    headline: str
    summary: str
    lean: str | None = None  # supportive | cautious | mixed | insufficient
    lean_detail: str | None = None
    caveats: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class DirectionSummary(BaseModel):
    """Directional evidence counted three ways so nothing is double-counted."""
    items_up: int = 0
    items_down: int = 0
    items_neutral: int = 0
    directional_items: int = 0          # up + down items (after collapsing duplicates)
    duplicates_collapsed: int = 0       # near-identical headlines counted once
    long_horizon_excluded: int = 0      # e.g. "by 2030" forecasts when the question is about next month
    unique_sources: int = 0
    sources_up: int = 0
    sources_down: int = 0
    sources_mixed: int = 0
    surfaces_up: list[str] = Field(default_factory=list)
    surfaces_down: list[str] = Field(default_factory=list)
    share_up: float | None = None       # sources_up / (sources_up + sources_down)
    lean: str = "insufficient"          # upward | downward | mixed | insufficient
    note: str = ""


class RegionSummary(BaseModel):
    region: str
    items: int = 0
    unique_sources: int = 0
    sources_up: int = 0
    sources_down: int = 0
    lean: str = "insufficient"
    trend_direction: str | None = None
    trend_change_pct: float | None = None
    trend_window: str | None = None
    top_headlines: list[dict] = Field(default_factory=list)   # {title, source, url, stance, id}
    evidence_ids: list[str] = Field(default_factory=list)


class RegionalComparison(BaseModel):
    regions: list[RegionSummary] = Field(default_factory=list)
    agrees: bool | None = None
    finding: str = ""
    caveats: list[str] = Field(default_factory=list)


class DataQuality(BaseModel):
    # Surface counts mean unique information channels; task counts include
    # separate regional searches for the same channel.
    surfaces_planned: int = 0
    surfaces_completed: int = 0
    surfaces_failed: int = 0
    surfaces_empty: int = 0
    surfaces_with_evidence: int = 0     # == surfaces_completed; surfaces_planned = completed + empty + failed
    unique_sources: int = 0
    trend_windows: list[str] = Field(default_factory=list)
    reconciled: bool = True
    tasks_planned: int = 0
    tasks_attempted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_empty: int = 0
    raw_results: int = 0
    kept_results: int = 0
    dropped_irrelevant: int = 0
    dated_share: float = 0.0
    notes: list[str] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    investigation_id: str
    plan: InvestigationPlan
    signals: list[Signal] = Field(default_factory=list)
    divergences: list[Divergence] = Field(default_factory=list)
    blind_spots: list[BlindSpot] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    claim_groups: list[ClaimGroup] = Field(default_factory=list)
    geo_findings: list[GeoFinding] = Field(default_factory=list)
    trend_series: list[TrendSeries] = Field(default_factory=list)
    surface_status: list[SurfaceStatus] = Field(default_factory=list)
    verdict: Verdict | None = None
    direction: DirectionSummary | None = None
    regional: RegionalComparison | None = None
    data_quality: DataQuality | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    entity_profiles: list[EntityProfile] = Field(default_factory=list)
    temporal_context: TemporalContext | None = None
    context_coverage: ContextCoverage | None = None
    cross_surface_findings: list[CrossSurfaceFinding] = Field(default_factory=list)
    claim_clusters: list[dict] = Field(default_factory=list)
    generated_at: datetime
    provenance: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
