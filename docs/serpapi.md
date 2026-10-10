# SerpApi integration

| Surface | Engine | Query param | Notes |
|---|---|---|---|
| Web | `google` | `q` | `num` ≤ 100, answer box captured |
| News | `google_news` | `q` | `iso_date` / `MM/DD/YYYY, HH:MM AM, +0000 UTC` parsed; `stories` flattened |
| Trends | `google_trends` | `q` | `data_type=TIMESERIES`, `date`, `geo`; **no `num`**; analysed as a time series |
| Scholar | `google_scholar` | `q` | `num` ≤ 20; year parsed from `publication_info.summary` |
| Jobs | `google_jobs` | `q` | `detected_extensions.posted_at` |
| Shopping | `google_shopping` | `q` | 50 s timeout, retries, fallback query |
| Patents | `google_patents` | `q` | `num` 10–100; filing/publication dates |
| Video | `youtube` | **`search_query`** | `published_date` |

`backend/serpapi/engines.py::build_params` encodes these rules. `client.py` adds per-engine timeouts, exponential-backoff retries
for transient errors, "no results" handling (not an error), and a TTL cache. `agent/router.py` retries empty/failed tasks with simpler fallback queries.
