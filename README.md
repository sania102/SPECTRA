# SPECTRA: Information Blind-Spot Intelligence
**DEMO  : https://drive.google.com/file/d/1hjoiCVWl-e5avcEi23SKGfel1c55loAd/view?usp=sharing**

> **Search wider. See what you're missing.**
> Built for the **SerpApi India Hackathon 2026** · Track 01 – AI Agents

Ask a question. SPECTRA's agent searches **Google News, Trends, Web, Scholar, Jobs, Shopping, Patents and YouTube through SerpApi**, scores what each source shows, and tells you **where they disagree**. Those gaps are the *blind spots* a normal search hides. For example, "everyone is talking about it, but nobody is hiring or selling it".

---

## What you get

| | |
|---|---|
| **Answer to your question** | A direct answer ("Not yet", "Leans up", "Evidence is split"), the evidence for and against (with links), what can't be concluded, and next steps. |
| **Signal map** | One High / Medium / Low signal per information surface. |
| **Blind spots** | Where attention and real-world activity disagree, with evidence, counter-evidence and "what could make this wrong". |
| **Who says what** | Direction counted by *unique source*, with duplicates and other-period forecasts removed. |
| **Regional comparison** | Global vs India (or any regions you pick) side by side, with linked headlines. |
| **Trends** | Google Trends with the requested window shown and a 30-day change that is comparable across modes. |
| **Audit** | Exactly which SerpApi searches ran, what came back and what was filtered out. |
| **History** | Past investigations are saved: replay them for free, or delete them. |



---

## Where SerpApi is used (the core of the project)

**All evidence comes from SerpApi.** Every result, link, date and trend value in a report is returned by a live SerpApi search. Without SerpApi, SPECTRA has nothing to analyse.

| What | File |
|---|---|
| SerpApi HTTP client: timeouts, retries, caching, "no results" handling | `backend/serpapi/client.py` |
| Per-engine request rules (`q` vs `search_query`, `gl`, `geo`, Trends window…) | `backend/serpapi/engines.py` |
| Turns each engine's JSON into one evidence format | `backend/serpapi/parsers/*.py` |
| The agent that chooses which engines to call for a question | `backend/agent/planner.py` |
| Runs the searches in parallel, retries with simpler queries | `backend/agent/router.py` |

**SerpApi engines used:** `google`, `google_news`, `google_trends`, `google_scholar`, `google_jobs`, `google_shopping`, `google_patents`, `youtube`. The agent picks only the engines the question needs, not all of them every time.

## Where AI (OpenAI) is used

The LLM is **optional** and uses any OpenAI-compatible API (`LLM_API_KEY`, `LLM_MODEL`; default `gpt-4o-mini`). Code: `backend/llm/` (`client.py`, `service.py`).

It is used **only for wording**:
1. Refining the short search query for each surface (`enrich_plan`)
2. Labelling each result with a one-line claim and direction (`extract_claims`)
3. Rewriting blind-spot explanations in plain language (`explain_blind_spot`)


---

## How it works

```
Question ─▶ Planner (picks surfaces) ─▶ SerpApi searches (parallel) ─▶ Clean & filter off-topic
        ─▶ Signals per surface ─▶ Divergences ─▶ Blind spots ─▶ Answer + evidence + audit
```

1. **Plan:** classify the question (forecast? maturity? regional?) and choose surfaces, queries, trend window and regions.
2. **Search:** call SerpApi for each surface (live progress streams to the UI).
3. **Clean:** remove duplicates and results that don't mention the subject.
4. **Measure:** score each surface (relevance × volume × freshness; Trends from the real time series).
5. **Compare:** find surfaces that disagree, such as high attention but low hiring or availability.
6. **Answer:** write a direct, honest answer with links. SPECTRA reports what the evidence shows and **never predicts**.

Folder map: `backend/agent` (planner, router, investigator) · `backend/serpapi` · `backend/analysis` (signals, divergence, blind spots, answer, direction, geo) · `backend/llm` · `backend/api` · `frontend/` (Next.js UI) · `tests/` · `docs/`.

---

## Run it locally

**Prerequisites:** Python 3.11+, Node 20+, a free [SerpApi key](https://serpapi.com/users/sign_up) (250 searches/month). An LLM key is optional.

```bash
# 1. Backend  (run from the repo root)
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp .env.example .env                 # then edit .env and add your keys
uvicorn backend.app.main:app --reload --port 8000

# 2. Frontend  (new terminal)
cd frontend
npm install
npm run dev                          # open http://localhost:3000
```

`.env` settings:

| Variable | Required | Purpose |
|---|---|---|
| `SERPAPI_API_KEY` | **yes** | Live search data |
| `LLM_API_KEY` | no | Enables AI wording (OpenAI or compatible) |
| `LLM_MODEL` | no | Default `gpt-4o-mini` |
| `LLM_BASE_URL` | no | For OpenAI-compatible providers (Gemini, Groq, OpenRouter…) |

Open `http://localhost:8000/api/llm/check` to test your LLM setup, and `http://localhost:8000/docs` for the API.



## Run the tests

```bash
pip install pytest
python -m pytest tests -q      # 28 offline tests, no API keys needed
```

## Using the app

1. Type a question, choose **Quick / Standard / Deep**, optionally pick regions to compare.
2. Click **Run investigation**. You jump straight to the live pipeline and watch each SerpApi search finish.
3. Read the **Answer**, then explore the tabs: *Answer & blind spots · Evidence · Regions & trends · Data source & audit*.
4. Past investigations appear on the home page: click to replay, or 🗑 to delete (or *Clear all*).

Good first questions: *"Is humanoid robotics actually commercially mature?"*, *"If I buy silver today, will the price go up by next month?"*, *"Is EV adoption in India accelerating faster than infrastructure?"*


