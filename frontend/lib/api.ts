import type { Depth, InvestigationResult, RunSummary, StreamEvent } from "@/types/investigation";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail.map((d: { msg?: string }) => d.msg).join("; ");
  } catch { /* fall through */ }
  return `Request failed (${res.status})`;
}

/** Streams a live investigation (Server-Sent Events over fetch). */
export async function streamInvestigation(
  question: string, depth: Depth, regions: string[], onEvent: (e: StreamEvent) => void, signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/investigations/stream`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, depth, regions }), signal,
    });
  } catch {
    throw new Error("Cannot reach the SPECTRA backend. Is it running on " + API_BASE_URL + " ?");
  }
  if (!res.ok || !res.body) throw new Error(await readError(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try { onEvent(JSON.parse(line.slice(6)) as StreamEvent); } catch { /* ignore malformed frame */ }
    }
  }
}

export async function fetchDemo(scenario: "humanoid" | "silver" = "humanoid"): Promise<InvestigationResult> {
  const res = await fetch(`${API_BASE_URL}/investigations/demo?scenario=${scenario}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchRuns(): Promise<RunSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/investigations/runs`);
    return res.ok ? await res.json() : [];
  } catch { return []; }
}

export async function fetchRun(id: string): Promise<InvestigationResult> {
  const res = await fetch(`${API_BASE_URL}/investigations/runs/${id}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteRun(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/investigations/runs/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export async function clearRuns(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/investigations/runs`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}
