"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";

export const SURFACES: Record<string, { label: string; icon: string; color: string; what: string; signal: string }> = {
  web: { label: "Google Search", icon: "🔎", color: "#3b82f6", what: "what the open web says", signal: "Public Web Presence" },
  news: { label: "Google News", icon: "📰", color: "#f472b6", what: "what the media is covering", signal: "News Momentum" },
  trends: { label: "Google Trends", icon: "📈", color: "#22d3ee", what: "what people actually search for", signal: "Public Attention" },
  scholar: { label: "Google Scholar", icon: "🎓", color: "#8b5cf6", what: "what researchers are publishing", signal: "Research Activity" },
  jobs: { label: "Google Jobs", icon: "💼", color: "#34d399", what: "who is hiring (real-world adoption)", signal: "Hiring Demand" },
  shopping: { label: "Google Shopping", icon: "🛒", color: "#fbbf24", what: "what you can actually buy", signal: "Commercial Availability" },
  patents: { label: "Google Patents", icon: "💡", color: "#fb923c", what: "what is being invented", signal: "Patent Activity" },
  video: { label: "YouTube", icon: "▶️", color: "#f87171", what: "what people show and discuss on video", signal: "Video Attention" },
};
// evidence "source_type" values differ from surface keys
export const TYPE_TO_SURFACE: Record<string, string> = {
  web: "web", news: "news", attention: "trends", research: "scholar", jobs: "jobs", commercial: "shopping", patent: "patents", video: "video",
};
export const SIGNAL_COLOR: Record<string, string> = Object.fromEntries(Object.values(SURFACES).map((s) => [s.signal, s.color]));
export const SIGNAL_ICON: Record<string, string> = Object.fromEntries(Object.values(SURFACES).map((s) => [s.signal, s.icon]));

export function surfaceOf(typeOrSurface: string | null | undefined): string {
  if (!typeOrSurface) return "web";
  return TYPE_TO_SURFACE[typeOrSurface] ?? typeOrSurface;
}

export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") { setShown(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } }, { threshold: 0.08 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={`reveal ${shown ? "in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms` }}>{children}</div>;
}

export function Explain({ children, icon = "💡" }: { children: ReactNode; icon?: string }) {
  return <div className="explain"><span aria-hidden>{icon}</span><div>{children}</div></div>;
}

export function SectionTitle({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div className="eyebrow">{eyebrow}</div>
      <h2 style={{ fontSize: 30, fontWeight: 800, margin: "6px 0 4px", letterSpacing: "-.02em" }}>{title}</h2>
      {sub && <p className="muted" style={{ margin: 0, maxWidth: 760, lineHeight: 1.55 }}>{sub}</p>}
    </div>
  );
}

export function Ring({ value, color = "var(--cyan)", label }: { value: number; color?: string; label?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div title={label} className="ring" style={{ ["--p" as string]: pct, ["--c" as string]: color } as React.CSSProperties}>
      <span>{pct}%</span>
    </div>
  );
}

export function LevelBadge({ level }: { level: string }) {
  return <span className={`chip lvl-${level}`} style={{ textTransform: "uppercase", letterSpacing: ".06em", fontSize: 11 }}>{level}</span>;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
