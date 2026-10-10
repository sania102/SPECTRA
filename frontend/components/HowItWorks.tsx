"use client";
import { Reveal, SectionTitle } from "./shared";

const STEPS = [
  { n: "1", icon: "🧠", title: "The agent plans", body: "SPECTRA reads your question and decides which information surfaces matter — it never blindly calls every API." },
  { n: "2", icon: "📡", title: "SerpApi gathers live evidence", body: "Google Search, News, Trends, Scholar, Jobs, Shopping, YouTube and Patents are queried in parallel with short, targeted queries." },
  { n: "3", icon: "⚖️", title: "Signals are measured", body: "Each surface gets a transparent score. Off-topic results are removed. Everything is deterministic and auditable." },
  { n: "4", icon: "🕳️", title: "Blind spots are exposed", body: "Where one surface is loud and another is silent, or sources contradict each other, SPECTRA flags it — with the evidence and what could make it wrong." },
];

export default function HowItWorks() {
  return (
    <section style={{ maxWidth: 1120, margin: "0 auto", padding: "30px 20px 70px" }}>
      <Reveal><SectionTitle eyebrow="How it works" title="Not another search box. An investigation." sub="A search engine shows you results. ChatGPT gives you an answer. SPECTRA shows you where the information landscape disagrees with itself." /></Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 16 }}>
        {STEPS.map((s, i) => (
          <Reveal key={s.n} delay={i * 110}>
            <div className="glass glass-hover" style={{ padding: 22, height: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="float" style={{ fontSize: 34, animationDelay: `${i * 0.4}s` }}>{s.icon}</span>
                <span className="chip">Step {s.n}</span>
              </div>
              <h3 style={{ margin: "14px 0 6px", fontSize: 19 }}>{s.title}</h3>
              <p className="muted" style={{ margin: 0, lineHeight: 1.55, fontSize: 14.5 }}>{s.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={200}>
        <div className="glass" style={{ marginTop: 18, padding: 22, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 18 }}>
          <div><div className="eyebrow">Example</div><p style={{ margin: "6px 0 0", lineHeight: 1.55 }}>“Is humanoid robotics commercially mature?” — News ↑↑↑, Search ↑↑↑, Research ↑↑, but Shopping ↓ and Jobs ↓.</p></div>
          <div><div className="eyebrow" style={{ color: "var(--amber)" }}>Blind spot</div><p style={{ margin: "6px 0 0", lineHeight: 1.55 }}>Public attention may be running far ahead of what is actually for sale. That&apos;s what a single search never tells you.</p></div>
        </div>
      </Reveal>
    </section>
  );
}
