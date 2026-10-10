"use client";
import { useEffect, useState } from "react";
import { SURFACES } from "./shared";

// Illustrative values only (clearly labelled), so a first-time visitor understands the idea in seconds.
const DEMO: { key: string; v: number }[] = [
  { key: "news", v: 0.92 }, { key: "video", v: 0.85 }, { key: "web", v: 0.88 }, { key: "trends", v: 0.78 },
  { key: "scholar", v: 0.6 }, { key: "patents", v: 0.52 }, { key: "jobs", v: 0.16 }, { key: "shopping", v: 0.08 },
];

export function Steps() {
  const steps = [["1", "Ask", "Type any question", "#8b5cf6"], ["2", "Investigate", "An AI agent picks the right Google surfaces via SerpApi", "#22d3ee"],
    ["3", "Compare", "Signals from every surface are scored", "#34d399"], ["4", "Reveal", "See where they disagree: your blind spots", "#f472b6"]];
  return (
    <div className="fade-up" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 10, margin: "0 auto 26px", maxWidth: 900, animationDelay: ".2s" }}>
      {steps.map(([n, t, d, c]) => (
        <div key={n} className="glass" style={{ padding: "12px 14px", textAlign: "left", display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ width: 34, height: 34, flex: "none", borderRadius: "50%", display: "grid", placeItems: "center", fontWeight: 800, background: c + "33", border: `1px solid ${c}`, color: c }}>{n}</span>
          <div><div style={{ fontWeight: 700, fontSize: 15 }}>{t}</div><div className="dim" style={{ fontSize: 12.5, lineHeight: 1.35 }}>{d}</div></div>
        </div>
      ))}
    </div>
  );
}

export default function HeroPreview() {
  const [on, setOn] = useState(false);
  const [cycle, setCycle] = useState(0);
  useEffect(() => {
    const a = setTimeout(() => setOn(true), 500);
    const loop = setInterval(() => { setOn(false); setTimeout(() => { setCycle((c) => c + 1); setOn(true); }, 450); }, 9000);
    return () => { clearTimeout(a); clearInterval(loop); };
  }, []);
  return (
    <div className="glass" style={{ maxWidth: 820, margin: "36px auto 0", padding: 22, textAlign: "left", position: "relative", overflow: "hidden" }} aria-label="Illustrative preview of a SPECTRA result">
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div className="eyebrow">What you get · illustrative preview</div>
        <span className="chip" style={{ fontSize: 11 }}>“Is humanoid robotics commercially mature?”</span>
      </div>
      <div key={cycle} style={{ display: "grid", gap: 9, marginTop: 16 }}>
        {DEMO.map((d, i) => {
          const s = SURFACES[d.key];
          const low = d.v < 0.3;
          return (
            <div key={d.key} style={{ display: "grid", gridTemplateColumns: "150px 1fr 56px", gap: 10, alignItems: "center", fontSize: 13.5 }}>
              <span>{s.icon} {s.label.replace("Google ", "")}</span>
              <div className="track"><div className="fill" style={{ width: on ? `${d.v * 100}%` : "0%", transition: `width 1.1s ${i * 0.12}s cubic-bezier(.2,.8,.2,1)`, background: low ? "linear-gradient(90deg,#f87171,#fb923c)" : s.color }} /></div>
              <span className={`chip ${low ? "lvl-low" : d.v > 0.62 ? "lvl-high" : "lvl-medium"}`} style={{ justifyContent: "center", padding: "2px 8px" }}>{low ? "Low" : d.v > 0.62 ? "High" : "Med"}</span>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 16, padding: "12px 14px", borderRadius: 14, border: "1px solid rgba(251,191,36,.5)", background: "rgba(251,191,36,.08)", opacity: on ? 1 : 0, transform: on ? "none" : "translateY(10px)", transition: "all .6s 1.5s" }}>
        <b style={{ color: "var(--amber)" }}>🕳️ Blind spot detected</b>
        <div className="muted" style={{ fontSize: 14, marginTop: 4, lineHeight: 1.5 }}>News, video and search buzz are <b style={{ color: "#fff" }}>very high</b>, but hiring and things you can actually buy are <b style={{ color: "#fff" }}>very low</b>. Public attention may be running ahead of real-world adoption.</div>
      </div>
    </div>
  );
}
