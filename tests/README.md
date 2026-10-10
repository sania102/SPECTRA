# Tests

Run from the repository root (needs `pip install -r backend/requirements.txt`):

```bash
python -m pytest tests -q          # or: python tests/test_pipeline.py
python -m compileall -q backend
```

`test_pipeline.py` drives the whole agent with a fake SerpApi client (no network or keys). It covers:
per-engine request parameters, short topic queries, Trends time-series analysis, Shopping timeout → fallback
query, off-topic filtering, News-date parsing, disagreement / claim-group detection, coverage blind spots,
divergence → blind-spot generation, geographic planning, and LLM-output sanitisation.
