"use client";
import type { Disagreement, Divergence, EvidenceItem, InvestigationResult, TrendSeries } from "@/types/investigation";
import { Explain, Reveal, SIGNAL_COLOR, SIGNAL_ICON, SURFACES, SectionTitle, fmtDate } from "./shared";

export function Divergences({ r }: { r: InvestigationResult }) {
  const sig = new Map(r.signals.map((s) => [s.name, s]));
  return (
    <section id="divergences" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Step 2 · Divergences" title="Where do the surfaces disagree?"
        sub="A divergence is a meaningful gap between two surfaces — e.g. everyone is talking about it, but almost nothing is for sale." /></Reveal>
      {r.divergences.length === 0 ? (
        <div className="glass" style={{ padding: 22 }}>No meaningful gap between the surfaces SPECTRA could observe.</div>
      ) : (
        <div style={{ display: "grid", gap: 14 }}>
          {r.divergences.map((d: Divergence, i) => {
            const hi = sig.get(d.higher_signal ?? d.left_signal), lo = sig.get(d.lower_signal ?? d.right_signal);
            return (
              <Reveal key={d.id} delay={i * 80}>
                <div className="glass glass-hover" style={{ padding: 20 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
                    <span className="chip" style={{ color: "var(--pink)" }}>{d.kind === "momentum" ? "🚀 Early-signal divergence" : "⚡ Level divergence"}</span>
                    <span className="chip">Gap {d.magnitude.toFixed(2)}</span><span className="chip">Confidence {(d.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 14, alignItems: "center" }}>
                    {[hi, lo].map((s, k) => s && (
                      <div key={k} style={{ gridColumn: k === 0 ? 1 : 3 }}>
                        <div style={{ fontWeight: 700, marginBottom: 6 }}>{SIGNAL_ICON[s.name]} {s.name}</div>
                        <div className="track" style={{ height: 12 }}><div className="fill bar-fill" style={{ width: `${s.strength * 100}%`, background: SIGNAL_COLOR[s.name] }} /></div>
                        <div className="dim" style={{ fontSize: 12, marginTop: 4 }}>{s.level} · {s.strength.toFixed(2)}</div>
                      </div>
                    ))}
                    <div style={{ gridColumn: 2, gridRow: 1, fontSize: 24 }} className="float">⇄</div>
                  </div>
                  <p className="muted" style={{ margin: "12px 0 0", lineHeight: 1.55, fontSize: 14.5 }}>{d.explanation}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
      )}
    </section>
  );
}

function EvList({ ids, byId }: { ids: string[]; byId: Map<string, EvidenceItem> }) {
  return <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13.5, lineHeight: 1.5 }}>{ids.slice(0, 5).map((id) => { const e = byId.get(id); return e ? <li key={id}>{e.url ? <a href={e.url} target="_blank" rel="noreferrer" style={{ color: "#bcd0ff" }}>{e.title}</a> : e.title} <span className="dim">— {e.source}</span></li> : null; })}</ul>;
}

export function Disagreements({ r }: { r: InvestigationResult }) {
  const byId = new Map(r.evidence.map((e) => [e.id, e]));
  if (r.disagreements.length === 0 && r.claim_groups.length === 0) return null;
  return (
    <section id="disagreements" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Claims & conflicts" title="What do sources agree and disagree on?" sub="SPECTRA groups repeated statements and flags where sources point in opposite directions." /></Reveal>
      <div style={{ display: "grid", gap: 14 }}>
        {r.disagreements.map((d: Disagreement) => (
          <Reveal key={d.id}>
            <div className="glass" style={{ padding: 20, borderColor: "rgba(251,146,60,.5)" }}>
              <div className="chip" style={{ color: "var(--orange)" }}>⚔️ {d.topic}</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 14, marginTop: 12 }}>
                <div style={{ padding: 14, borderRadius: 14, background: "rgba(52,211,153,.07)", border: "1px solid rgba(52,211,153,.3)" }}>
                  <b style={{ color: "var(--green)" }}>↗ {d.side_a_label}</b><div className="dim" style={{ fontSize: 12 }}>{d.side_a_sources} source(s)</div><EvList ids={d.side_a_evidence_ids} byId={byId} /></div>
                <div style={{ padding: 14, borderRadius: 14, background: "rgba(248,113,113,.07)", border: "1px solid rgba(248,113,113,.3)" }}>
                  <b style={{ color: "var(--red)" }}>↘ {d.side_b_label}</b><div className="dim" style={{ fontSize: 12 }}>{d.side_b_sources} source(s)</div><EvList ids={d.side_b_evidence_ids} byId={byId} /></div>
              </div>
              <p className="muted" style={{ margin: "12px 0 0", fontSize: 14 }}>{d.explanation}</p>
            </div>
          </Reveal>
        ))}
        {r.claim_groups.length > 0 && (
          <Reveal>
            <div className="glass" style={{ padding: 20 }}>
              <div className="eyebrow">Claim groups</div>
              <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
                {r.claim_groups.slice(0, 6).map((g) => (
                  <div key={g.id} style={{ display: "flex", justifyContent: "space-between", gap: 10, padding: "9px 12px", borderRadius: 12, background: "rgba(255,255,255,.04)", flexWrap: "wrap" }}>
                    <span>{g.stance === "up" ? "↗ " : g.stance === "down" ? "↘ " : ""}{g.label}</span>
                    <span style={{ display: "flex", gap: 6 }}><span className="chip">{g.claim_count} claims</span><span className={`chip ${g.corroborated ? "lvl-high" : ""}`}>{g.source_count} sources{g.corroborated ? " ✓ corroborated" : ""}</span></span>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        )}
      </div>
    </section>
  );
}

function Spark({ s }: { s: TrendSeries }) {
  const w = 600, h = 150, pad = 8;
  const max = Math.max(...s.values, 1), n = s.values.length;
  const pts = s.values.map((v, i) => [pad + (i / Math.max(1, n - 1)) * (w - pad * 2), h - pad - (v / max) * (h - pad * 2)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
  const area = `${line} L${pts[n - 1][0]},${h - pad} L${pts[0][0]},${h - pad} Z`;
  const up = s.direction === "rising", col = up ? "#34d399" : s.direction === "falling" ? "#f87171" : "#22d3ee";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%" }} role="img" aria-label={`Search interest for ${s.query} over time`}>
      <defs><linearGradient id={`sp${s.region ?? "x"}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={col} stopOpacity=".45" /><stop offset="100%" stopColor={col} stopOpacity="0" /></linearGradient></defs>
      <path d={area} fill={`url(#sp${s.region ?? "x"})`} /><path d={line} fill="none" stroke={col} strokeWidth="3" strokeLinejoin="round" className="draw" />
      <circle cx={pts[n - 1][0]} cy={pts[n - 1][1]} r="5" fill={col} stroke="#fff" strokeWidth="2" />
    </svg>
  );
}

export function TrendAndGeo({ r }: { r: InvestigationResult }) {
  if (r.trend_series.length === 0 && r.geo_findings.length === 0) return null;
  const regions = Array.from(new Set(r.geo_findings.map((g) => g.region)));
  const surfaces = Array.from(new Set(r.geo_findings.map((g) => g.surface)));
  return (
    <section id="time" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Time & place" title="Is it changing? Does it differ by region?" sub="Google Trends shows whether public interest is accelerating. Regional searches show whether the story changes by country." /></Reveal>
      <div style={{ display: "grid", gap: 14 }}>
        {r.trend_series.map((s, i) => (
          <Reveal key={i}><div className="glass" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <b>📈 Search interest: “{s.query}”{s.region ? ` · ${s.region}` : ""}</b>
              <span className={`chip ${s.direction === "rising" ? "lvl-high" : s.direction === "falling" ? "lvl-low" : "lvl-medium"}`}>{s.direction}{s.change_pct != null ? ` ${s.change_pct > 0 ? "+" : ""}${s.change_pct.toFixed(0)}%` : ""}</span>
            </div>
            <Spark s={s} />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "6px 0" }}>
              <span className="chip">🗓 Requested window: {s.window_label ?? s.window ?? "provider default"}</span>
              {s.span && <span className="chip">fetched {s.span} · {s.points} points</span>}
              {(s.horizons ?? []).map((h) => <span key={h.days} className={`chip ${h.direction === "rising" ? "lvl-high" : h.direction === "falling" ? "lvl-low" : "lvl-medium"}`}>{h.label}: {h.change_pct != null ? `${h.change_pct > 0 ? "+" : ""}${h.change_pct.toFixed(0)}%` : "n/a"}</span>)}
            </div>
            <div className="dim" style={{ fontSize: 12 }}>Index 0–100 relative to the topic&apos;s own peak. The headline change always uses the same yardstick (last 30 days vs the 30 days before) so Quick, Standard and Deep are comparable; longer horizons appear when the window is long enough. Attention is not a price signal.</div>
          </div></Reveal>
        ))}
        {r.geo_findings.length > 0 && (
          <Reveal><div className="glass" style={{ padding: 20, overflowX: "auto" }}>
            <b>🌍 Regional comparison</b>
            <table style={{ width: "100%", marginTop: 12, borderCollapse: "collapse", fontSize: 14 }}>
              <thead><tr><th style={{ textAlign: "left", padding: 8 }} className="dim">Region</th>{surfaces.map((s) => <th key={s} className="dim" style={{ padding: 8, textAlign: "left" }}>{SURFACES[s === "attention" ? "trends" : s === "research" ? "scholar" : s]?.icon} {s}</th>)}</tr></thead>
              <tbody>{regions.map((reg) => (
                <tr key={reg} style={{ borderTop: "1px solid var(--card-b)" }}><td style={{ padding: 8, fontWeight: 700 }}>{reg}</td>
                  {surfaces.map((sf) => { const g = r.geo_findings.find((x) => x.region === reg && x.surface === sf); return <td key={sf} style={{ padding: 8, minWidth: 120 }}>{g ? <><div className="track" style={{ height: 8 }}><div className="fill bar-fill" style={{ width: `${g.strength * 100}%`, background: "var(--spectrum)" }} /></div><div className="dim" style={{ fontSize: 11, marginTop: 3 }}>{g.strength.toFixed(2)} · {g.evidence_count} results · {g.source_count ?? 0} sources{g.note ? ` · ${g.note}` : ""}</div></> : <span className="dim">—</span>}</td>; })}</tr>
              ))}</tbody>
            </table>
          </div></Reveal>
        )}
      </div>
    </section>
  );
}

export function DataQualityPanel({ r }: { r: InvestigationResult }) {
  const q = r.data_quality;
  if (!q) return null;
  const color = { completed: "var(--green)", empty: "var(--amber)", failed: "var(--red)" } as const;
  return (
    <section id="quality" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Trust & audit" title="Data quality: what SPECTRA actually checked" sub="Transparency about failures and filtering, so you know how far to trust the result." /></Reveal>
      <Reveal><div className="glass" style={{ padding: 22 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
          {[["Surfaces with evidence", `${q.surfaces_completed}/${q.surfaces_planned}`], ["Surfaces empty / failed", `${q.surfaces_empty} / ${q.surfaces_failed}`], ["Unique sources", q.unique_sources ?? "—"], ["Search tasks attempted", q.tasks_attempted ?? q.tasks_planned ?? q.surfaces_planned], ["Search tasks completed", `${q.tasks_completed ?? q.surfaces_completed}/${q.tasks_planned ?? q.surfaces_planned}`], ["Tasks empty", q.tasks_empty ?? q.surfaces_empty], ["Tasks failed", q.tasks_failed ?? q.surfaces_failed], ["Raw results", q.raw_results], ["Kept as relevant", q.kept_results], ["Filtered off-topic", q.dropped_irrelevant], ["Dated evidence", `${Math.round(q.dated_share * 100)}%`]].map(([k, v]) => (
            <div key={String(k)} style={{ padding: 12, borderRadius: 14, background: "rgba(255,255,255,.05)" }}><div className="dim" style={{ fontSize: 12 }}>{k}</div><div style={{ fontSize: 24, fontWeight: 800 }}>{v}</div></div>
          ))}
        </div>
        <div style={{ overflowX: "auto", marginTop: 16 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
            <thead><tr className="dim" style={{ textAlign: "left" }}><th style={{ padding: 6 }}>Surface</th><th>Query used</th><th>Status</th><th>Results → kept</th><th>Tries</th><th>Time</th></tr></thead>
            <tbody>{r.surface_status.map((s) => (
              <tr key={s.task_id} style={{ borderTop: "1px solid var(--card-b)" }}>
                <td style={{ padding: 8 }}>{s.label}{s.region ? ` · ${s.region}` : ""}</td><td className="mono dim">“{s.query}”</td>
                <td style={{ color: color[s.status], fontWeight: 700 }}>{s.status}{s.error_kind ? ` (${s.error_kind})` : ""}</td>
                <td>{s.evidence_count} → {s.kept_count}</td><td>{s.attempts}</td><td>{(s.duration_ms / 1000).toFixed(1)}s</td>
              </tr>))}</tbody>
          </table>
        </div>
        {r.plan && <div className="dim" style={{ marginTop: 12, fontSize: 13 }}>Depth audit: <b>{r.plan.depth ?? "standard"}</b> · configured surface limit {r.plan.configured_surface_limit ?? "—"} · per-surface result limit {r.plan.per_surface_limit ?? "—"} · geography <b>{(r.plan.geographic_strategy ?? "global_overview").replaceAll("_", " ")}</b>. Trend windows requested: {r.plan.search_tasks.filter((t) => t.surface === "trends").map((t) => `${t.region ?? "Global"}: ${String(t.params?.date ?? "provider default")}`).join("; ") || "none"}. Surfaces = unique channels (News, Trends…); tasks = one search per channel per region. Surfaces planned = with evidence + empty + failed.</div>}
        {q.notes.length > 0 && <ul style={{ margin: "14px 0 0", paddingLeft: 18, lineHeight: 1.6, fontSize: 14 }} className="muted">{q.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
        {r.temporal_context && <div className="dim" style={{ marginTop: 10, fontSize: 13 }}>Timeline: {r.temporal_context.recent_count} recent (≤90d), {r.temporal_context.prior_count} older, {r.temporal_context.undated_count} undated, {r.temporal_context.snapshot_count} live snapshots · attention is <b>{r.temporal_context.direction}</b>.</div>}
      </div></Reveal>
    </section>
  );
}

export function Methodology() {
  return (
    <section id="method" style={{ scrollMarginTop: 90 }}>
      <Reveal>
        <details className="glass" style={{ padding: 22 }}>
          <summary><span className="eyebrow">Methodology · how every number is computed ▾</span></summary>
          <div style={{ marginTop: 14, display: "grid", gap: 12, lineHeight: 1.6, fontSize: 14.5 }} className="muted">
            <p style={{ margin: 0 }}><b style={{ color: "#fff" }}>The AI never decides the scores.</b> An LLM (optional) only refines search wording, extracts claims and rewrites explanations. Signals, divergences and blind spots are deterministic.</p>
            <div className="mono" style={{ fontSize: 12.5, padding: 14, borderRadius: 12, background: "rgba(0,0,0,.3)", whiteSpace: "pre-wrap" }}>{`relevance      = 0.55·anchor-coverage + 0.20·key-terms + 0.15·rank + 0.10·title-match
quality        = mean(0.70·relevance + 0.30·freshness)
volume         = min(1, n/8)^0.8
signal         = quality · (0.25 + 0.75·volume)          # ~5+ relevant items needed for "high"
trends signal  = 0.60·level + 0.40·momentum               # from the real time series
divergence     = |signal_A − signal_B|  (needs gap ≥ 0.22, stronger ≥ 0.45, confidence ≥ 0.40)
blind-spot     importance = 0.55·gap + 0.25·stronger + 0.20·confidence`}</div>
            <p style={{ margin: 0 }}>Results that never mention the investigated subject are removed. A surface that fails is reported as <b style={{ color: "#fff" }}>unobserved</b> — never silently scored as &ldquo;low&rdquo;. Strength is evidence strength, <b style={{ color: "#fff" }}>not a probability</b>.</p>
          </div>
        </details>
      </Reveal>
    </section>
  );
}
