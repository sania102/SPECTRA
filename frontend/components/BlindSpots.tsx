"use client";
import { useState } from "react";
import type { BlindSpot, EvidenceItem, InvestigationResult } from "@/types/investigation";
import { Explain, Reveal, Ring, SectionTitle, SURFACES, fmtDate, surfaceOf } from "./shared";

const KIND: Record<string, { icon: string; label: string; color: string }> = {
  divergence: { icon: "⚡", label: "Signals diverge", color: "#f472b6" },
  coverage: { icon: "🔦", label: "Not observed", color: "#fbbf24" },
  temporal: { icon: "⏳", label: "Time unclear", color: "#22d3ee" },
  disagreement: { icon: "⚔️", label: "Sources disagree", color: "#fb923c" },
};

function EvidenceLine({ e }: { e: EvidenceItem }) {
  const meta = SURFACES[surfaceOf(e.source_type)] ?? SURFACES.web;
  return (
    <div style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--card-b)", fontSize: 13.5 }}>
      <span title={meta.label}>{meta.icon}</span>
      <div style={{ minWidth: 0 }}>
        {e.url ? <a href={e.url} target="_blank" rel="noreferrer" style={{ color: "#bcd0ff", fontWeight: 600 }}>{e.title}</a> : <b>{e.title}</b>}
        <div className="dim" style={{ fontSize: 12 }}>{e.source}{e.published_at ? ` · ${fmtDate(e.published_at)}` : e.date_kind === "observed" ? " · live snapshot" : ""}</div>
      </div>
    </div>
  );
}

function Card({ b, r, i }: { b: BlindSpot; r: InvestigationResult; i: number }) {
  const [open, setOpen] = useState(i === 0);
  const k = KIND[b.kind] ?? KIND.divergence;
  const byId = new Map(r.evidence.map((e) => [e.id, e]));
  const ev = b.evidence_ids.map((id) => byId.get(id)).filter((e): e is EvidenceItem => !!e);
  const claims = ev.filter((e) => e.claim).slice(0, 4);
  return (
    <Reveal delay={i * 90}>
      <div className="glass glass-hover" style={{ padding: 24, borderColor: k.color + "66", boxShadow: `0 0 0 1px ${k.color}22, 0 22px 60px -30px ${k.color}` }}>
        <div style={{ display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ display: "grid", justifyItems: "center", gap: 4 }}>
            <Ring value={b.confidence} color={k.color} label="Confidence" /><span className="dim" style={{ fontSize: 11 }}>confidence</span>
          </div>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <span className="chip" style={{ color: k.color, borderColor: k.color + "88" }}>{k.icon} {k.label}</span>
              <span className="chip">🕳️ Potential blind spot #{i + 1}</span>
            </div>
            <h3 style={{ fontSize: 22, margin: "10px 0 8px", lineHeight: 1.25 }}>{b.title}</h3>
            <p className="muted" style={{ margin: 0, lineHeight: 1.6 }}>{b.description}</p>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
              <span className="dim" style={{ fontSize: 12 }}>Importance</span>
              <div className="track" style={{ width: 150, height: 7 }}><div className="fill bar-fill" style={{ width: `${b.importance * 100}%`, background: k.color }} /></div>
            </div>
          </div>
        </div>

        <button className="btn btn-ghost" style={{ marginTop: 16, padding: "9px 16px", fontSize: 13 }} onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "▲ Hide" : "▼ Show"} why SPECTRA concluded this
        </button>

        {open && (
          <div className="fade-up" style={{ marginTop: 16, display: "grid", gap: 16 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 13 }}>
              <span className="chip">Conclusion</span>→
              {b.supporting_signals.length > 0 ? b.supporting_signals.map((s) => <span key={s} className="chip">{s}</span>) : <span className="chip">Source headlines</span>}→
              <span className="chip">{ev.length} evidence items</span>→<span className="chip">Sources (links below)</span>
            </div>
            {claims.length > 0 && (
              <div><div className="eyebrow">Claims behind it</div>
                <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 14 }} className="muted">{claims.map((c) => <li key={c.id}>{c.claim}</li>)}</ul></div>
            )}
            {ev.length > 0 && <div><div className="eyebrow">Evidence (real SerpApi results)</div>{ev.slice(0, 8).map((e) => <EvidenceLine key={e.id} e={e} />)}</div>}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 14 }}>
              <div style={{ padding: 14, borderRadius: 14, background: "rgba(248,113,113,.08)", border: "1px solid rgba(248,113,113,.3)" }}>
                <div className="eyebrow" style={{ color: "var(--red)" }}>What could make this wrong</div>
                <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 13.5 }}>{b.what_could_make_this_wrong.map((w, j) => <li key={j}>{w}</li>)}</ul>
              </div>
              {b.counter_evidence.length > 0 && (
                <div style={{ padding: 14, borderRadius: 14, background: "rgba(52,211,153,.07)", border: "1px solid rgba(52,211,153,.3)" }}>
                  <div className="eyebrow" style={{ color: "var(--green)" }}>Counter-evidence</div>
                  <ul style={{ margin: "6px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 13.5 }}>{b.counter_evidence.map((w, j) => <li key={j}>{w}</li>)}</ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Reveal>
  );
}

export default function BlindSpots({ r }: { r: InvestigationResult }) {
  return (
    <section id="blindspots" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Step 3 · The hero finding" title={`${r.blind_spots.length} potential blind spot${r.blind_spots.length === 1 ? "" : "s"}`}
        sub="A blind spot is something the easy-to-see information may be hiding from you: a surface that disagrees, a dimension nobody could observe, or sources that contradict each other." /></Reveal>
      {r.blind_spots.length === 0 ? (
        <div className="glass" style={{ padding: 24 }}>✅ No material blind spot found among the surfaces SPECTRA could observe. See the data-quality panel for what was and wasn&apos;t checked.</div>
      ) : <div style={{ display: "grid", gap: 18 }}>{r.blind_spots.map((b, i) => <Card key={b.id} b={b} r={r} i={i} />)}</div>}
      <div style={{ marginTop: 12 }}><Explain>Blind spots are <b>prompts to look closer</b>, never proof. Each card lists what could make it wrong.</Explain></div>
    </section>
  );
}
