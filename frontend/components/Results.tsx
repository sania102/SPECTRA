"use client";
import { useState } from "react";
import type { InvestigationResult } from "@/types/investigation";
import { AnswerCard } from "./Answer";
import BlindSpots from "./BlindSpots";
import EvidenceExplorer from "./EvidenceExplorer";
import { DirectionPanel, ModeAudit, RegionalPanel, SerpApiPanel } from "./Insights";
import { DataQualityPanel, Disagreements, Divergences, Methodology, TrendAndGeo } from "./Panels";
import { SignalMap } from "./SignalMap";

type Tab = "answer" | "evidence" | "regions" | "audit";

export default function Results({ r, isDemo, onReset }: { r: InvestigationResult; isDemo: boolean; onReset: () => void }) {
  const [tab, setTab] = useState<Tab>("answer");
  const hasRegions = !!r.regional || r.trend_series.length > 0 || r.geo_findings.length > 0;
  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: "answer", label: "Answer & blind spots", badge: r.blind_spots.length },
    { id: "evidence", label: "Evidence", badge: r.evidence.length },
    ...(hasRegions ? [{ id: "regions" as Tab, label: "Regions & trends" }] : []),
    { id: "audit", label: "Data source & audit" },
  ];
  const download = () => {
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `spectra-${r.investigation_id}.json`; a.click(); URL.revokeObjectURL(a.href);
  };
  return (
    <div style={{ maxWidth: 1120, margin: "0 auto", padding: "10px 20px 80px", display: "grid", gap: 28 }}>
      {isDemo && <div className="glass" style={{ padding: 14, borderColor: "var(--amber)", textAlign: "center" }}>⚠ <b>Sample data</b>: the real SPECTRA pipeline run over canned responses. Run your own question for live SerpApi evidence.</div>}
      <div>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div><div className="eyebrow">Investigation complete ✓</div><h1 style={{ fontSize: "clamp(22px,3.6vw,34px)", margin: "6px 0 0", letterSpacing: "-.02em" }}>“{r.plan.question}”</h1></div>
          <div className="no-print" style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost" onClick={download}>⬇ JSON</button><button className="btn btn-ghost" onClick={() => window.print()}>🖨 Print</button><button className="btn" onClick={onReset}>＋ New investigation</button>
          </div>
        </div>
        <div className="spectrum-bar" style={{ marginTop: 14 }} />
      </div>

      <nav className="sticky-nav glass no-print" style={{ padding: 6, display: "flex", gap: 4, overflowX: "auto" }} role="tablist" aria-label="Report sections">
        {tabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => { setTab(t.id); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            className="nav-pill" style={{ cursor: "pointer", color: tab === t.id ? "#fff" : undefined, background: tab === t.id ? "linear-gradient(135deg,#8b5cf6,#3b82f6)" : "transparent", border: "none", fontSize: 14 }}>
            {t.label}{t.badge ? <span style={{ marginLeft: 8, opacity: .8 }}>· {t.badge}</span> : null}
          </button>
        ))}
      </nav>

      {tab === "answer" && (<div style={{ display: "grid", gap: 44 }}><AnswerCard r={r} /><SignalMap r={r} /><BlindSpots r={r} /></div>)}
      {tab === "evidence" && (<div style={{ display: "grid", gap: 44 }}><DirectionPanel r={r} /><Disagreements r={r} /><Divergences r={r} /><EvidenceExplorer r={r} /></div>)}
      {tab === "regions" && (<div style={{ display: "grid", gap: 44 }}><RegionalPanel r={r} /><TrendAndGeo r={r} /></div>)}
      {tab === "audit" && (<div style={{ display: "grid", gap: 20 }}><SerpApiPanel r={r} /><DataQualityPanel r={r} /><ModeAudit r={r} /><Methodology /></div>)}
    </div>
  );
}
