"use client";
import type { Answer, AnswerPoint, InvestigationResult } from "@/types/investigation";
import { Reveal } from "./shared";

const TONE: Record<string, string> = { positive: "var(--green)", negative: "var(--orange)", mixed: "var(--amber)", unknown: "var(--muted)" };

function Points({ title, color, items, empty }: { title: string; color: string; items: AnswerPoint[]; empty: string }) {
  return (
    <div>
      <div className="eyebrow" style={{ color }}>{title}</div>
      <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "grid", gap: 10 }}>
        {items.length === 0 && <li className="dim" style={{ fontSize: 14 }}>{empty}</li>}
        {items.map((p, i) => (
          <li key={i} style={{ fontSize: 14.5, lineHeight: 1.5 }}>
            {p.text}
            {p.links.map((l) => (
              <a key={l.url} href={l.url ?? undefined} target="_blank" rel="noreferrer" className="dim" style={{ display: "block", fontSize: 12.5, marginTop: 2, textDecoration: "underline", textUnderlineOffset: 3 }}>
                ↗ {l.source ? `${l.source}: ` : ""}{l.title}
              </a>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnswerCard({ r }: { r: InvestigationResult }) {
  const a: Answer | null | undefined = r.verdict?.answer;
  if (!a) return null;
  const color = TONE[a.tone] ?? "var(--muted)";
  return (
    <Reveal>
      <div className="glass" style={{ padding: "28px 28px 24px", position: "relative", overflow: "hidden", borderColor: color }}>
        <div className="spectrum-bar" style={{ position: "absolute", left: 0, right: 0, top: 0 }} />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
          <div className="eyebrow">Answer to your question</div>
          <span className="chip" title={a.confidence_reason}>Evidence confidence: <b style={{ textTransform: "capitalize" }}>{a.confidence}</b></span>
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap", marginTop: 14 }}>
          <span className="pop" style={{ padding: "8px 18px", borderRadius: 999, fontWeight: 800, fontSize: 20, color: "#0b1128", background: color }}>{a.label}</span>
        </div>
        <p style={{ fontSize: "clamp(18px,2.3vw,23px)", lineHeight: 1.45, margin: "14px 0 0", fontWeight: 600, maxWidth: 900 }}>{a.direct_answer}</p>
        {a.regional_note && <div className="explain" style={{ marginTop: 14 }}>🌍 <span>{a.regional_note}</span></div>}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 22, marginTop: 22 }}>
          <Points title="✓ What supports it" color="var(--green)" items={a.evidence_for} empty="No strong supporting signal was found." />
          <Points title="✗ What argues against it" color="var(--orange)" items={a.evidence_against} empty="No notable contradicting signal was found." />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 22, marginTop: 22, paddingTop: 18, borderTop: "1px solid var(--card-b)" }}>
          <div><div className="eyebrow" style={{ color: "var(--amber)" }}>⚠ What we can&apos;t conclude</div>
            <ul className="muted" style={{ margin: "10px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 14 }}>{a.uncertainty.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
          <div><div className="eyebrow" style={{ color: "var(--cyan)" }}>→ What to do next</div>
            <ul className="muted" style={{ margin: "10px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 14 }}>{a.next_steps.map((u, i) => <li key={i}>{u}</li>)}</ul></div>
        </div>
      </div>
    </Reveal>
  );
}
