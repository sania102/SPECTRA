"use client";
import type { InvestigationResult, RegionSummary } from "@/types/investigation";
import { Reveal, SectionTitle } from "./shared";

const LEAN_COLOR: Record<string, string> = { upward: "var(--green)", downward: "var(--red)", mixed: "var(--amber)", insufficient: "var(--dim)" };
const stanceIcon = (s: string | null) => (s === "up" ? "▲" : s === "down" ? "▼" : "•");

/** Items vs unique sources: shows that SPECTRA does not let one publisher dominate the verdict. */
export function DirectionPanel({ r }: { r: InvestigationResult }) {
  const d = r.direction;
  if (!d || (d.directional_items === 0 && d.items_neutral === 0)) return null;
  const total = Math.max(1, d.sources_up + d.sources_down + d.sources_mixed);
  const seg = (n: number, c: string) => <div style={{ width: `${(n / total) * 100}%`, background: c, transition: "width 1s" }} />;
  return (
    <section id="direction" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Who says what" title="Which way does the coverage lean — and how independent is it?"
        sub="Every count below is shown three ways so nothing is double-counted: headlines, unique sources, and what was removed." /></Reveal>
      <Reveal><div className="glass" style={{ padding: 22 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
          <div><span className="dim" style={{ fontSize: 13 }}>Evidence lean (by unique source) </span>
            <b style={{ color: LEAN_COLOR[d.lean] ?? "#fff", fontSize: 20, textTransform: "capitalize" }}>{d.lean}</b></div>
          {d.share_up != null && <span className="chip">{Math.round(d.share_up * 100)}% of deciding sources lean up</span>}
        </div>
        <div style={{ display: "flex", height: 16, borderRadius: 999, overflow: "hidden", margin: "14px 0", background: "rgba(255,255,255,.08)" }}
          role="img" aria-label={`${d.sources_up} sources lean up, ${d.sources_down} lean down`}>
          {seg(d.sources_up, "var(--green)")}{seg(d.sources_mixed, "var(--amber)")}{seg(d.sources_down, "var(--red)")}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 10 }}>
          {[["▲ Sources leaning up", d.sources_up], ["▼ Sources leaning down", d.sources_down], ["Unique sources", d.unique_sources],
            ["Directional headlines", d.directional_items], ["Duplicates counted once", d.duplicates_collapsed], ["Other-period forecasts excluded", d.long_horizon_excluded]].map(([k, v]) => (
            <div key={String(k)} style={{ padding: 12, borderRadius: 14, background: "rgba(255,255,255,.05)" }}>
              <div className="dim" style={{ fontSize: 12 }}>{k}</div><div style={{ fontSize: 24, fontWeight: 800 }}>{v}</div></div>
          ))}
        </div>
        <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.6, margin: "14px 0 0" }}>{d.note} Search interest is attention, not a price direction, so it is excluded from this count.</p>
      </div></Reveal>
    </section>
  );
}

function RegionCard({ s }: { s: RegionSummary }) {
  return (
    <div className="glass glass-hover" style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <b style={{ fontSize: 18 }}>{s.region === "Global" ? "🌍" : "📍"} {s.region}</b>
        <span className="chip" style={{ color: LEAN_COLOR[s.lean], borderColor: LEAN_COLOR[s.lean] }}>coverage: {s.lean}</span>
      </div>
      <div className="muted" style={{ fontSize: 13.5, marginTop: 8, lineHeight: 1.6 }}>
        {s.unique_sources} unique sources · <span style={{ color: "var(--green)" }}>▲ {s.sources_up}</span> vs <span style={{ color: "var(--red)" }}>▼ {s.sources_down}</span><br />
        {s.trend_direction ? <>Search interest <b style={{ color: "#fff" }}>{s.trend_direction}</b>{s.trend_change_pct != null ? ` (${s.trend_change_pct > 0 ? "+" : ""}${s.trend_change_pct.toFixed(0)}% / 30 days)` : ""}{s.trend_window ? ` · ${s.trend_window}` : ""}</> : "No search-interest series"}
      </div>
      <div style={{ display: "grid", gap: 6, marginTop: 12 }}>
        {s.top_headlines.map((h) => (
          <a key={h.id} href={h.url ?? undefined} target="_blank" rel="noreferrer" style={{ textDecoration: "none", fontSize: 13, padding: "8px 10px", borderRadius: 10, background: "rgba(255,255,255,.05)", display: "block" }}>
            <span style={{ color: h.stance === "up" ? "var(--green)" : "var(--red)" }}>{stanceIcon(h.stance)}</span> {h.title}
            <div className="dim" style={{ fontSize: 11, marginTop: 2 }}>{h.source}</div>
          </a>
        ))}
      </div>
    </div>
  );
}

export function RegionalPanel({ r }: { r: InvestigationResult }) {
  const g = r.regional;
  if (!g) return null;
  const color = g.agrees === false ? "var(--amber)" : g.agrees ? "var(--green)" : "var(--muted)";
  return (
    <section id="regions" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Regional comparison" title={`Do ${g.regions.map((x) => x.region).join(" and ")} tell the same story?`}
        sub="The same question searched with different country settings. Disagreement between regions is itself a blind spot." /></Reveal>
      <Reveal><div className="glass" style={{ padding: 18, marginBottom: 14, borderColor: color }}>
        <b style={{ color }}>{g.agrees === false ? "⚠ Regions disagree" : g.agrees ? "✓ Regions broadly agree" : "Regional read"}</b>
        <div className="muted" style={{ marginTop: 6, fontSize: 14.5, lineHeight: 1.6 }}>{g.finding}</div>
      </div></Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 14 }}>
        {g.regions.map((s) => <Reveal key={s.region}><RegionCard s={s} /></Reveal>)}
      </div>
      <ul className="dim" style={{ fontSize: 12.5, marginTop: 12, paddingLeft: 18 }}>{g.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul>
    </section>
  );
}

/** Proves what each mode actually executed (configured vs attempted vs completed). */
export function ModeAudit({ r }: { r: InvestigationResult }) {
  const m = r.plan.mode_profile, q = r.data_quality;
  if (!m || !q) return null;
  const windows = r.trend_series.map((s) => `${s.region ?? "Global"}: ${s.window_label ?? s.window ?? "?"} (${s.points ?? s.values.length} pts${s.span ? `, ${s.span}` : ""})`);
  const rows: [string, string][] = [
    ["Mode", `${m.label}: ${m.goal}`],
    ["Designed to", m.summary],
    ["Surfaces", `${q.surfaces_planned} planned (limit ${m.surface_limit}) = ${q.surfaces_completed} with evidence + ${q.surfaces_empty} empty + ${q.surfaces_failed} failed`],
    ["Search tasks", `${q.tasks_planned} planned (${q.surfaces_planned} surfaces × regions) → ${q.tasks_completed} completed, ${q.tasks_empty} empty, ${q.tasks_failed} failed`],
    ["Results", `${q.raw_results} raw → ${q.kept_results} kept (${q.dropped_irrelevant} off-topic removed) from ${q.unique_sources ?? "?"} unique sources`],
    ["Trend window executed", windows.join("; ") || "no Trends data returned"],
    ["Counts reconcile", q.reconciled === false ? "⚠ mismatch: please report" : "✓ yes"],
  ];
  return (
    <Reveal><div className="glass" style={{ padding: 20, marginTop: 14 }}>
      <div className="eyebrow">Mode audit · configured vs executed</div>
      <div style={{ display: "grid", gap: 6, marginTop: 10, fontSize: 14 }}>
        {rows.map(([k, v]) => <div key={k} style={{ display: "grid", gridTemplateColumns: "170px 1fr", gap: 10 }}><span className="dim">{k}</span><span>{v}</span></div>)}
      </div>
    </div></Reveal>
  );
}

/** Proof of what is SerpApi (all evidence) vs what is the LLM (wording only). */
export function SerpApiPanel({ r }: { r: InvestigationResult }) {
  const m = r.metadata as Record<string, any>;
  const byEngine = new Map<string, { label: string; searches: number; raw: number; kept: number }>();
  r.surface_status.forEach((s) => {
    const e = byEngine.get(s.engine) ?? { label: s.label, searches: 0, raw: 0, kept: 0 };
    e.searches += s.attempts; e.raw += s.evidence_count; e.kept += s.kept_count; byEngine.set(s.engine, e);
  });
  const total = Array.from(byEngine.values()).reduce((a, e) => a + e.searches, 0);
  const llmOn = !!m.llm_enabled;
  return (
    <Reveal><div className="glass" style={{ padding: 22 }}>
      <div className="eyebrow">Where the data comes from</div>
      <h3 style={{ margin: "8px 0 4px", fontSize: 20 }}>🔎 100% of the evidence is live SerpApi search data</h3>
      <p className="muted" style={{ margin: "0 0 14px", fontSize: 14, lineHeight: 1.6 }}>{total} SerpApi search request(s) across {byEngine.size} engines returned every result, link, date and trend value in this report.</p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead><tr className="dim" style={{ textAlign: "left" }}><th style={{ padding: 6 }}>SerpApi engine</th><th>Searches</th><th>Results returned</th><th>Kept as relevant</th></tr></thead>
          <tbody>{Array.from(byEngine.entries()).map(([k, e]) => (
            <tr key={k} style={{ borderTop: "1px solid var(--card-b)" }}><td style={{ padding: 8 }}>{e.label} <span className="mono dim">({k})</span></td><td>{e.searches}</td><td>{e.raw}</td><td>{e.kept}</td></tr>))}</tbody>
        </table>
      </div>
      <div className="explain" style={{ marginTop: 14 }}>🤖 <span>
        <b>AI language model ({llmOn ? String(m.llm_model ?? "enabled") : "not configured"}):</b> used only for wording, never for data or scores: refining search queries ({m.llm_used_for_enrichment ? "used" : "not used"}), labelling claims ({m.claims_added_by_llm ?? 0} labelled), and rewriting blind-spot explanations ({m.llm_blindspot_explanations ?? 0} rewritten).
        Signals, divergences, blind spots and the answer are computed by deterministic code from the SerpApi evidence.</span></div>
    </div></Reveal>
  );
}
