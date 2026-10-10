"use client";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import LiveInvestigation, { initialLive, liveReducer } from "@/components/LiveInvestigation";
import Results from "@/components/Results";
import { clearRuns, deleteRun, fetchDemo, fetchRun, fetchRuns, streamInvestigation } from "@/lib/api";
import type { Depth, InvestigationResult, RunSummary } from "@/types/investigation";

type Phase = "idle" | "running" | "done";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [live, dispatch] = useReducer(liveReducer, undefined, initialLive);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const abort = useRef<AbortController | null>(null);
  const pipelineRef = useRef<HTMLDivElement | null>(null);
  const [asked, setAsked] = useState<{ question: string; depth: Depth } | null>(null);

  useEffect(() => { fetchRuns().then(setRuns); }, [phase]);

  const run = useCallback(async (question: string, depth: Depth, regions: string[]) => {
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    setError(null); setResult(null); setIsDemo(false); setAsked({ question, depth });
    dispatch({ type: "stage", stage: "__reset__", message: "Starting…" });
    setPhase("running");
    // jump straight to the live pipeline as soon as the user clicks "Run investigation"
    requestAnimationFrame(() => requestAnimationFrame(() => pipelineRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })));
    let finished = false;
    try {
      await streamInvestigation(question, depth, regions, (e) => {
        if (e.type === "result") { finished = true; setResult(e.result); setPhase("done"); window.scrollTo({ top: 0, behavior: "smooth" }); }
        else if (e.type === "error") { finished = true; setError(e.message); setPhase("idle"); }
        else dispatch(e);
      }, ctrl.signal);
      if (!finished) { setError("The connection closed before the investigation finished."); setPhase("idle"); }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError((err as Error).message); setPhase("idle");
    }
  }, []);

  const showStatic = useCallback(async (loader: () => Promise<InvestigationResult>, demo: boolean) => {
    setError(null);
    try { const r = await loader(); setResult(r); setIsDemo(demo); setPhase("done"); window.scrollTo({ top: 0 }); }
    catch (err) { setError((err as Error).message); }
  }, []);

  const removeRun = useCallback(async (id: string) => {
    try { await deleteRun(id); setRuns((rs) => rs.filter((r) => r.id !== id)); }
    catch (err) { setError((err as Error).message); }
  }, []);
  const removeAll = useCallback(async () => {
    try { await clearRuns(); setRuns([]); }
    catch (err) { setError((err as Error).message); }
  }, []);

  const reset = () => { abort.current?.abort(); setPhase("idle"); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <main>
      {phase !== "done" && <div style={{ display: phase === "running" ? "none" : "block" }}><Hero busy={phase === "running"} runs={runs} onRun={run} onDelete={removeRun} onClearAll={removeAll} onDemo={(s) => showStatic(() => fetchDemo(s), true)} onReplay={(id) => showStatic(() => fetchRun(id), false)} /></div>}
      {error && (
        <div role="alert" className="glass fade-up" style={{ maxWidth: 760, margin: "10px auto 30px", padding: 18, borderColor: "var(--red)" }}>
          <b style={{ color: "var(--red)" }}>Something went wrong</b><div className="muted" style={{ marginTop: 6 }}>{error}</div>
        </div>
      )}
      {phase === "running" && (
        <div ref={pipelineRef} style={{ scrollMarginTop: 12 }}>
          <div className="glass fade-up" style={{ maxWidth: 1040, margin: "20px auto 0", padding: "14px 18px", display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
            <div style={{ minWidth: 0 }}>
              <div className="eyebrow">Investigating · {asked?.depth ?? "standard"} mode</div>
              <div style={{ fontWeight: 700, fontSize: 18, marginTop: 4 }}>“{asked?.question}”</div>
            </div>
            <button className="btn btn-ghost" style={{ padding: "9px 16px", fontSize: 13 }} onClick={reset}>✕ Cancel</button>
          </div>
          <LiveInvestigation state={live} />
        </div>
      )}
      {phase === "done" && result && <Results r={result} isDemo={isDemo} onReset={reset} />}
      {phase === "idle" && <HowItWorks />}
      <footer className="dim" style={{ textAlign: "center", padding: "24px 20px 40px", fontSize: 13 }}>
        SPECTRA · built for the SerpApi India Hackathon 2026 · evidence from live SerpApi searches · signals are not predictions
      </footer>
    </main>
  );
}
