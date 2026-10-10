"use client";
import { useState } from "react";
import type { Depth, RunSummary } from "@/types/investigation";
import { SURFACES } from "./shared";
import HeroPreview, { Steps } from "./HeroPreview";

const EXAMPLES = [
  { q: "Is humanoid robotics actually commercially mature?", tag: "Attention vs reality" },
  { q: "If I buy silver today, will the price go up by next month?", tag: "Direction & disagreement" },
  { q: "Is EV adoption in India accelerating faster than infrastructure?", tag: "Market + geography" },
  { q: "Is AI coding becoming a mainstream developer job skill?", tag: "Jobs vs hype" },
];
const REGION_CHOICES = ["Global", "India", "United States", "United Kingdom", "European Union", "Japan", "China", "Australia"];
const DEPTHS: { id: Depth; name: string; note: string }[] = [
  { id: "quick", name: "Quick", note: "3 surfaces · 3-month trend · fastest" },
  { id: "standard", name: "Standard", note: "5 surfaces · 12-month trend · Global vs India cross-check" },
  { id: "deep", name: "Deep", note: "8 surfaces · 5-year trend · research check · 20 results each" },
];

interface Props {
  busy: boolean; runs: RunSummary[];
  onRun: (question: string, depth: Depth, regions: string[]) => void; onDemo: (scenario: "humanoid" | "silver") => void; onReplay: (id: string) => void;
  onDelete: (id: string) => void; onClearAll: () => void;
}

export default function Hero({ busy, runs, onRun, onDemo, onReplay, onDelete, onClearAll }: Props) {
  const [regions, setRegions] = useState<string[]>([]);
  const toggleRegion = (r: string) => setRegions((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : cur.length >= 4 ? cur : [...cur, r]));
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState<Depth>("standard");
  const ready = question.trim().length >= 8 && !busy;
  const chips = Object.values(SURFACES);

  return (
    <section style={{ maxWidth: 1040, margin: "0 auto", padding: "64px 20px 24px", textAlign: "center" }}>
      <div className="fade-up" style={{ display: "inline-flex", gap: 10, alignItems: "center", marginBottom: 22 }}>
        <span className="chip"><span className="live-dot" /> Powered by live SerpApi data</span>
        <span className="chip">🤖 AI Agent</span>
      </div>

      <h1 className="fade-up" style={{ fontSize: "clamp(52px, 11vw, 112px)", fontWeight: 900, letterSpacing: "-.045em", lineHeight: .95, margin: 0, animationDelay: ".05s" }}>
        <span className="spectrum-text" style={{ display: "inline-block", paddingRight: ".08em" }}>SPECTRA</span>
      </h1>
      <p className="fade-up" style={{ fontSize: "clamp(20px, 3.4vw, 30px)", fontWeight: 700, margin: "16px 0 8px", animationDelay: ".12s" }}>
        Search wider. See what you&apos;re missing.
      </p>
      <p className="fade-up muted" style={{ fontSize: 18, maxWidth: 720, margin: "0 auto 30px", lineHeight: 1.6, animationDelay: ".18s" }}>
        Ask any question. SPECTRA checks <b style={{ color: "#fff" }}>news, search trends, research, jobs, shopping, video and patents</b> —
        then shows you where they <b style={{ color: "#fff" }}>disagree</b>. Those gaps are the information blind spots a normal search hides.
      </p>

      <Steps />

      <div className="fade-up" style={{ animationDelay: ".24s", textAlign: "left" }}>
        <div className="ask-wrap">
          <div className="ask-inner">
            <label htmlFor="q" className="eyebrow" style={{ display: "block", marginBottom: 8 }}>What do you want to investigate?</label>
            <textarea id="q" className="ask" rows={2} value={question} maxLength={600} disabled={busy}
              placeholder="e.g. Is humanoid robotics actually commercially mature?"
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && ready) { e.preventDefault(); onRun(question.trim(), depth, regions); } }} />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
              <div role="radiogroup" aria-label="Investigation depth" style={{ display: "flex", gap: 6, flexWrap: "wrap" }} title={DEPTHS.find((d) => d.id === depth)?.note}>
                {DEPTHS.map((d) => (
                  <button key={d.id} role="radio" aria-checked={depth === d.id} onClick={() => setDepth(d.id)} title={d.note}
                    className="chip" style={{ cursor: "pointer", color: depth === d.id ? "#fff" : "var(--muted)", background: depth === d.id ? "linear-gradient(135deg,#8b5cf6,#3b82f6)" : undefined, borderColor: depth === d.id ? "transparent" : undefined }}>
                    {d.name}<span className="dim" style={{ fontWeight: 500, color: depth === d.id ? "#dbe4ff" : undefined }}>· {d.note.split(" · ")[0]}</span>
                  </button>
                ))}
              </div>
              <button className="btn" disabled={!ready} onClick={() => onRun(question.trim(), depth, regions)}>
                {busy ? <><span className="spinner" /> Investigating…</> : <>🚀 Run investigation</>}
              </button>
            </div>
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--card-b)" }}>
              <div className="dim" style={{ fontSize: 12.5, marginBottom: 8 }}>🌍 Compare regions <span style={{ opacity: .7 }}>(optional · pick up to 4 · leave empty and SPECTRA decides)</span></div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {REGION_CHOICES.map((rg) => {
                  const on = regions.includes(rg);
                  return <button key={rg} type="button" aria-pressed={on} disabled={busy} onClick={() => toggleRegion(rg)} className="chip"
                    style={{ cursor: "pointer", color: on ? "#fff" : "var(--muted)", background: on ? "linear-gradient(135deg,#22d3ee,#3b82f6)" : undefined, borderColor: on ? "transparent" : undefined }}>{on ? "✓ " : ""}{rg}</button>;
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 26 }}>
        <div className="dim" style={{ fontSize: 13, marginBottom: 10 }}>Not sure what to ask? Try one of these:</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
          {EXAMPLES.map((ex) => (
            <button key={ex.q} className="glass glass-hover" disabled={busy} onClick={() => setQuestion(ex.q)}
              style={{ padding: "10px 16px", cursor: "pointer", color: "var(--text)", textAlign: "left", maxWidth: 330, fontSize: 14 }}>
              <div style={{ fontWeight: 600 }}>{ex.q}</div>
              <div className="eyebrow" style={{ fontSize: 10, marginTop: 4, color: "var(--pink)" }}>{ex.tag}</div>
            </button>
          ))}
        </div>
        <div style={{ marginTop: 16 }}>
          <div className="dim" style={{ fontSize: 12.5, marginBottom: 10 }}>{DEPTHS.find((d) => d.id === depth)?.note}</div>
          <button className="btn" style={{ padding: "11px 20px", fontSize: 14 }} disabled={busy} onClick={() => onDemo("humanoid")}>
            ▶ Watch a sample investigation (instant, no API calls)
          </button>{" "}
         
        </div>
      </div>

      <HeroPreview />

      <div className="marquee-wrap" style={{ marginTop: 40 }} aria-hidden>
        <div className="marquee">
          {[...chips, ...chips].map((s, i) => (
            <span key={i} className="chip" style={{ borderColor: s.color + "66", color: "#fff", fontSize: 13, padding: "8px 14px" }}>
              {s.icon} {s.label} <span className="dim" style={{ fontWeight: 400 }}>· {s.what}</span>
            </span>
          ))}
        </div>
      </div>

      {runs.length > 0 && (
        <div className="glass" style={{ marginTop: 34, padding: 18, textAlign: "left" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <div className="eyebrow">Recent investigations · replay instantly, no credits used</div>
            {confirmAll ? (
              <span style={{ display: "inline-flex", gap: 6, alignItems: "center", fontSize: 13 }}>
                Delete all {runs.length}?
                <button className="chip" style={{ cursor: "pointer", color: "#fff", background: "rgba(248,113,113,.3)", borderColor: "var(--red)" }} onClick={() => { setConfirmAll(false); onClearAll(); }}>Yes, delete all</button>
                <button className="chip" style={{ cursor: "pointer", color: "var(--muted)" }} onClick={() => setConfirmAll(false)}>Cancel</button>
              </span>
            ) : (
              <button className="chip" style={{ cursor: "pointer", color: "var(--muted)" }} disabled={busy} onClick={() => setConfirmAll(true)}>🗑 Clear all</button>
            )}
          </div>
          <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
            {runs.slice(0, 8).map((r) => (
              <div key={r.id} style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
                <button className="glass-hover" onClick={() => onReplay(r.id)} disabled={busy}
                  style={{ flex: 1, display: "flex", justifyContent: "space-between", gap: 12, padding: "10px 14px", borderRadius: 12, border: "1px solid var(--card-b)", background: "rgba(255,255,255,.04)", color: "var(--text)", cursor: "pointer", textAlign: "left" }}>
                  <span>{r.question}</span><span className="chip" style={{ flex: "none" }}>🕳️ {r.blind_spots}</span>
                </button>
                {confirmId === r.id ? (
                  <span style={{ display: "inline-flex", gap: 6, alignItems: "center", fontSize: 13, flex: "none" }}>
                    <button className="chip" style={{ cursor: "pointer", color: "#fff", background: "rgba(248,113,113,.3)", borderColor: "var(--red)" }} onClick={() => { setConfirmId(null); onDelete(r.id); }}>Delete</button>
                    <button className="chip" style={{ cursor: "pointer", color: "var(--muted)" }} onClick={() => setConfirmId(null)}>Keep</button>
                  </span>
                ) : (
                  <button aria-label={`Delete investigation: ${r.question}`} title="Delete this investigation" disabled={busy} onClick={() => setConfirmId(r.id)}
                    style={{ flex: "none", width: 42, borderRadius: 12, border: "1px solid var(--card-b)", background: "rgba(255,255,255,.04)", color: "var(--muted)", cursor: "pointer", fontSize: 16 }}>🗑</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
