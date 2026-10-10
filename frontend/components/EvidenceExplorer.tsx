"use client";
import { useMemo, useState } from "react";
import type { InvestigationResult } from "@/types/investigation";
import { Reveal, SURFACES, SectionTitle, fmtDate, surfaceOf } from "./shared";

export default function EvidenceExplorer({ r }: { r: InvestigationResult }) {
  const [filter, setFilter] = useState("all");
  const [text, setText] = useState("");
  const [limit, setLimit] = useState(12);
  const counts = useMemo(() => { const c: Record<string, number> = {}; r.evidence.forEach((e) => { const k = surfaceOf(e.source_type); c[k] = (c[k] ?? 0) + 1; }); return c; }, [r.evidence]);
  const shown = r.evidence.filter((e) => (filter === "all" || surfaceOf(e.source_type) === filter) && (!text || (e.title + " " + (e.snippet ?? "")).toLowerCase().includes(text.toLowerCase())));
  return (
    <section id="evidence" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Proof" title={`Evidence · ${r.evidence.length} real results`} sub="Every conclusion traces back to these actual SerpApi results — with source, date and link." /></Reveal>
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          <button className="chip" onClick={() => setFilter("all")} style={{ cursor: "pointer", background: filter === "all" ? "var(--violet)" : undefined }}>All {r.evidence.length}</button>
          {Object.entries(counts).map(([k, n]) => { const m = SURFACES[k]; return <button key={k} className="chip" onClick={() => setFilter(k)} style={{ cursor: "pointer", borderColor: m?.color, background: filter === k ? m?.color + "55" : undefined }}>{m?.icon} {m?.label ?? k} {n}</button>; })}
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Filter evidence…" aria-label="Filter evidence"
            style={{ marginLeft: "auto", padding: "8px 14px", borderRadius: 999, border: "1px solid var(--card-b)", background: "rgba(255,255,255,.05)", color: "var(--text)", outline: 0, minWidth: 180 }} />
        </div>
        <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
          {shown.slice(0, limit).map((e) => {
            const m = SURFACES[surfaceOf(e.source_type)] ?? SURFACES.web;
            return (
              <div key={e.id} style={{ display: "flex", gap: 12, padding: 14, borderRadius: 14, background: "rgba(255,255,255,.04)", borderLeft: `3px solid ${m.color}` }}>
                <span style={{ fontSize: 22 }}>{m.icon}</span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  {e.url ? <a href={e.url} target="_blank" rel="noreferrer" style={{ fontWeight: 700, color: "#cfdcff" }}>{e.title}</a> : <b>{e.title}</b>}
                  {e.snippet && <div className="muted" style={{ fontSize: 13.5, marginTop: 3, lineHeight: 1.5 }}>{e.snippet}</div>}
                  <div className="dim" style={{ fontSize: 12, marginTop: 6, display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <span>{e.source}</span>
                    <span>{e.published_at ? `📅 ${fmtDate(e.published_at)}` : e.date_kind === "observed" ? "📸 live snapshot" : "undated"}</span>
                    <span>relevance {(e.relevance * 100).toFixed(0)}%</span>
                    {e.stance === "up" && <span style={{ color: "var(--green)" }}>↗ upward</span>}{e.stance === "down" && <span style={{ color: "var(--red)" }}>↘ downward</span>}
                    {e.region && <span>🌍 {e.region}</span>}
                  </div>
                </div>
              </div>
            );
          })}
          {shown.length === 0 && <div className="dim">No evidence matches this filter.</div>}
        </div>
        {shown.length > limit && <button className="btn btn-ghost" style={{ marginTop: 14 }} onClick={() => setLimit(limit + 20)}>Show more ({shown.length - limit} left)</button>}
      </div>
    </section>
  );
}
