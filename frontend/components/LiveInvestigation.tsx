"use client";
import { useEffect, useState } from "react";
import type { Plan, StreamEvent } from "@/types/investigation";
import { SURFACES, surfaceOf } from "./shared";

export interface TaskLive {
  id: string; surface: string; label: string; query: string; region: string | null; rationale: string;
  status: "running" | "completed" | "empty" | "failed"; count: number; attempts: number; duration_ms: number; error?: string | null;
}
export interface LiveState {
  stage: string; message: string; plan: Plan | null; tasks: Record<string, TaskLive>; order: string[]; startedAt: number;
}
export const initialLive = (): LiveState => ({ stage: "understanding", message: "Understanding the question…", plan: null, tasks: {}, order: [], startedAt: Date.now() });

export function liveReducer(state: LiveState, e: StreamEvent): LiveState {
  switch (e.type) {
    case "stage": return { ...state, stage: e.stage, message: e.message };
    case "plan": return { ...state, plan: e.plan, stage: "searching" };
    case "task_start": return {
      ...state, order: state.order.includes(e.task_id) ? state.order : [...state.order, e.task_id],
      tasks: { ...state.tasks, [e.task_id]: { id: e.task_id, surface: e.surface, label: e.label, query: e.query, region: e.region, rationale: e.rationale, status: "running", count: 0, attempts: 1, duration_ms: 0 } },
    };
    case "task_done": {
      const prev = state.tasks[e.task_id];
      return { ...state, tasks: { ...state.tasks, [e.task_id]: { ...(prev ?? { id: e.task_id, surface: e.surface, label: e.label, region: e.region, rationale: "" }), query: e.query, status: e.status, count: e.count, attempts: e.attempts, duration_ms: e.duration_ms, error: e.error } as TaskLive } };
    }
    default: return state;
  }
}

const PIPELINE = [
  { id: "understanding", label: "Understanding your question" },
  { id: "searching", label: "Searching live data through SerpApi" },
  { id: "filtering", label: "Removing duplicates & off-topic results" },
  { id: "claims", label: "Extracting claims & direction" },
  { id: "signals", label: "Measuring signal strength" },
  { id: "divergence", label: "Comparing surfaces for disagreement" },
  { id: "blindspots", label: "Hunting for blind spots" },
  { id: "explaining", label: "Writing explanations" },
];

export default function LiveInvestigation({ state }: { state: LiveState }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - state.startedAt) / 1000)), 500);
    return () => clearInterval(t);
  }, [state.startedAt]);

  const currentIdx = Math.max(0, PIPELINE.findIndex((p) => p.id === state.stage));
  const tasks = state.order.map((id) => state.tasks[id]);
  const done = tasks.filter((t) => t.status !== "running").length;
  const total = state.plan?.search_tasks.length ?? tasks.length;
  const progress = Math.min(97, Math.round(((currentIdx + (state.stage === "searching" && total ? done / total : 0)) / PIPELINE.length) * 100));

  return (
    <section style={{ maxWidth: 940, margin: "0 auto", padding: "20px 20px 60px" }} aria-live="polite">
      <div className="glass fade-up" style={{ padding: 26 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}><span className="live-dot" /><span className="eyebrow">Live investigation</span></div>
          <span className="chip mono">⏱ {elapsed}s</span>
        </div>
        <h2 style={{ fontSize: 24, margin: "10px 0 6px" }}>{state.plan ? <>Investigating <span className="spectrum-text">{state.plan.topic}</span></> : "Planning the investigation…"}</h2>
        <p className="muted" style={{ margin: "0 0 14px" }}>{state.message}</p>
        <div className="track" style={{ height: 8 }}><div className="fill" style={{ width: `${progress}%`, background: "var(--spectrum)", transition: "width .6s ease" }} /></div>

        {state.plan && (
          <div className="fade-up" style={{ marginTop: 20, padding: 14, borderRadius: 14, border: "1px dashed var(--card-b)" }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>🧠 The agent&apos;s plan</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, fontSize: 13 }}>
              <span className="chip">Type: {state.plan.intent.replace("_", " ")}</span>
              {state.plan.is_forecast && <span className="chip" style={{ color: "var(--amber)" }}>🔮 Forward-looking question</span>}
              {state.plan.regions.length > 0 && <span className="chip">🌍 {state.plan.regions.join(" · ")}</span>}
              <span className="chip">Must mention: {state.plan.anchor_terms.join(", ") || "—"}</span>
              {state.plan.llm_refined && <span className="chip">✨ AI-refined queries</span>}
            </div>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(380px,1fr))", gap: 22, marginTop: 22 }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 10 }}>Pipeline</div>
            {PIPELINE.map((p, i) => {
              const isDone = i < currentIdx || state.stage === "done", isNow = i === currentIdx && state.stage !== "done";
              return (
                <div key={p.id} className="step-line" style={{ paddingBottom: 14, opacity: isDone || isNow ? 1 : .4, transition: "opacity .4s" }}>
                  <span style={{ position: "absolute", left: 0, top: 3 }}>
                    {isDone ? <span className="pop" style={{ color: "var(--green)", fontWeight: 900 }}>✓</span> : isNow ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, display: "block" }} /> : <span className="dim">○</span>}
                  </span>
                  <span style={{ fontWeight: isNow ? 700 : 500 }}>{p.label}</span>
                </div>
              );
            })}
          </div>

          <div>
            <div className="eyebrow" style={{ marginBottom: 10 }}>SerpApi searches · {done}/{total || "…"}</div>
            <div style={{ display: "grid", gap: 10 }}>
              {tasks.length === 0 && [0, 1, 2].map((k) => <div key={k} className="shimmer" style={{ height: 58, borderRadius: 14 }} />)}
              {tasks.map((t) => {
                const meta = SURFACES[surfaceOf(t.surface)] ?? SURFACES.web;
                return (
                  <div key={t.id} className="fade-up" style={{ padding: "11px 14px", borderRadius: 14, border: `1px solid ${meta.color}55`, background: `${meta.color}12`, display: "flex", gap: 12, alignItems: "center" }}>
                    <span style={{ fontSize: 22 }}>{meta.icon}</span>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{t.label}{t.region ? ` · ${t.region}` : ""}</div>
                      <div className="dim mono" style={{ fontSize: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>“{t.query}”</div>
                      {t.status === "failed" && <div style={{ fontSize: 12, color: "var(--red)" }}>Unavailable ({t.error ?? "error"}) — will be reported as unobserved</div>}
                    </div>
                    <div style={{ textAlign: "right", fontSize: 12, flex: "none" }}>
                      {t.status === "running" && <span className="spinner" />}
                      {t.status === "completed" && <span className="pop" style={{ color: "var(--green)", fontWeight: 700 }}>✓ {t.count} results</span>}
                      {t.status === "empty" && <span style={{ color: "var(--amber)", fontWeight: 700 }}>○ no results</span>}
                      {t.status === "failed" && <span style={{ color: "var(--red)", fontWeight: 700 }}>⚠ failed</span>}
                      {t.status !== "running" && <div className="dim">{(t.duration_ms / 1000).toFixed(1)}s{t.attempts > 1 ? ` · ${t.attempts} tries` : ""}</div>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
