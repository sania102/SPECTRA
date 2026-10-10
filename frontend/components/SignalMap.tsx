"use client";
import type { InvestigationResult, Signal } from "@/types/investigation";
import { Explain, LevelBadge, Reveal, SIGNAL_COLOR, SIGNAL_ICON, SURFACES, SectionTitle } from "./shared";

const ORDER = Object.values(SURFACES).map((s) => s.signal);
const TREND_ICON: Record<string, string> = { rising: "↗ rising", falling: "↘ falling", flat: "→ flat", active: "● recent", older: "◔ older", snapshot: "◉ live", undated: "? undated" };

export function Verdict({ r }: { r: InvestigationResult }) {
  const v = r.verdict;
  if (!v) return null;
  const leanColor = v.lean === "upward" ? "var(--green)" : v.lean === "downward" ? "var(--red)" : v.lean === "mixed" ? "var(--amber)" : "var(--muted)";
  return (
    <Reveal>
      <div className="glass" style={{ padding: 28, position: "relative", overflow: "hidden" }}>
        <div className="spectrum-bar" style={{ position: "absolute", left: 0, right: 0, top: 0 }} />
        <div className="eyebrow">Answer to your question</div>
        <h2 style={{ fontSize: "clamp(22px,3.4vw,32px)", margin: "8px 0 10px", lineHeight: 1.2, letterSpacing: "-.02em" }}>{v.headline}</h2>
        <p className="muted" style={{ fontSize: 16.5, lineHeight: 1.6, margin: 0, maxWidth: 860 }}>{v.summary}</p>
        {v.lean_detail && (
          <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 14, border: `1px solid ${leanColor}`, background: "rgba(255,255,255,.04)" }}>
            <b style={{ color: leanColor }}>Evidence lean: {v.lean}</b>
            <div className="muted" style={{ marginTop: 4, fontSize: 14 }}>{v.lean_detail}</div>
          </div>
        )}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 16, marginTop: 20 }}>
          <div><div className="eyebrow" style={{ color: "var(--amber)" }}>⚠ Read this first</div>
            <ul style={{ margin: "8px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 14 }} className="muted">{v.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
          <div><div className="eyebrow" style={{ color: "var(--green)" }}>→ What to do next</div>
            <ul style={{ margin: "8px 0 0", paddingLeft: 18, lineHeight: 1.55, fontSize: 14 }} className="muted">{v.next_steps.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
        </div>
      </div>
    </Reveal>
  );
}

function Radar({ signals }: { signals: Signal[] }) {
  const size = 340, c = size / 2, R = 112;
  const by = new Map(signals.map((s) => [s.name, s]));
  const pts = ORDER.map((name, i) => {
    const a = (Math.PI * 2 * i) / ORDER.length - Math.PI / 2;
    const s = by.get(name);
    const v = s ? Math.max(0.04, s.strength) : 0;
    return { name, a, v, x: c + Math.cos(a) * R * v, y: c + Math.sin(a) * R * v, lx: c + Math.cos(a) * (R + 30), ly: c + Math.sin(a) * (R + 30), has: !!s };
  });
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", maxWidth: 380 }} role="img" aria-label="Radar chart of signal strength by information surface">
      <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#8b5cf6" stopOpacity=".7" /><stop offset="100%" stopColor="#22d3ee" stopOpacity=".55" /></linearGradient></defs>
      {[0.25, 0.5, 0.75, 1].map((k) => <polygon key={k} points={ORDER.map((_, i) => { const a = (Math.PI * 2 * i) / ORDER.length - Math.PI / 2; return `${c + Math.cos(a) * R * k},${c + Math.sin(a) * R * k}`; }).join(" ")} fill="none" stroke="rgba(255,255,255,.12)" />)}
      {pts.map((p) => <line key={p.name} x1={c} y1={c} x2={c + Math.cos(p.a) * R} y2={c + Math.sin(p.a) * R} stroke="rgba(255,255,255,.1)" />)}
      <polygon className="fade-up" points={pts.map((p) => `${p.x},${p.y}`).join(" ")} fill="url(#rg)" stroke="#22d3ee" strokeWidth="2" strokeLinejoin="round" />
      {pts.map((p) => (
        <g key={p.name}>
          {p.has && <circle cx={p.x} cy={p.y} r="5" fill={SIGNAL_COLOR[p.name]} stroke="#fff" strokeWidth="1.5" />}
          <text x={p.lx} y={p.ly} textAnchor="middle" dominantBaseline="middle" fontSize="19" opacity={p.has ? 1 : 0.3}>{SIGNAL_ICON[p.name]}</text>
        </g>
      ))}
    </svg>
  );
}

export function SignalMap({ r }: { r: InvestigationResult }) {
  const observed = new Set(r.signals.map((s) => s.name));
  const missing = ORDER.filter((n) => !observed.has(n) && r.plan.search_tasks.some((t) => (SURFACES[t.surface]?.signal) === n));
  return (
    <section id="signals" style={{ scrollMarginTop: 90 }}>
      <Reveal><SectionTitle eyebrow="Step 1 · Signal map" title="How loud is the topic on each surface?"
        sub="Each Google surface shows a different side of reality: media attention, public curiosity, research, hiring, real products. Longer bar = stronger evidence on that surface." /></Reveal>
      <Reveal>
        <div className="glass" style={{ padding: 24, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 24, alignItems: "center" }}>
          <div style={{ display: "grid", placeItems: "center" }}><Radar signals={r.signals} /></div>
          <div style={{ display: "grid", gap: 14 }}>
            {r.signals.map((s, i) => (
              <div key={s.name} title={s.rationale ?? ""}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontWeight: 700 }}>{SIGNAL_ICON[s.name]} {s.name}</span>
                  <span style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }} className="muted">
                    {s.trend && <span>{TREND_ICON[s.trend] ?? s.trend}</span>}<span>{s.evidence_count} items</span><LevelBadge level={s.level} />
                  </span>
                </div>
                <div className="track"><div className="fill bar-fill" style={{ width: `${s.strength * 100}%`, background: SIGNAL_COLOR[s.name] ?? "var(--cyan)", animationDelay: `${i * 90}ms`, boxShadow: `0 0 18px ${SIGNAL_COLOR[s.name] ?? "#22d3ee"}88` }} /></div>
              </div>
            ))}
            {missing.map((n) => (
              <div key={n} className="dim" style={{ fontSize: 13, padding: "8px 12px", border: "1px dashed var(--card-b)", borderRadius: 12 }}>
                {SIGNAL_ICON[n]} <b>{n}</b> — not observed (search failed or returned nothing relevant). <i>Unobserved ≠ low.</i>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
      <div style={{ marginTop: 12 }}><Explain>Scores measure <b>how strong the evidence is on each surface</b> (relevance + freshness + volume). They are <b>not probabilities</b> — 72% does not mean &ldquo;72% likely&rdquo;.</Explain></div>
    </section>
  );
}
