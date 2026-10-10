# Methodology

All scores are deterministic and reproducible; the LLM (optional) never produces a score.

## Relevance
`relevance = 0.55·anchor_coverage + 0.20·key_term_coverage + 0.15·rank_prior + 0.10·title_match`.
Anchors are the subject words of the question (e.g. `silver`). Results covering < 50 % of anchors are dropped
(Google Trends is exempt: the query *is* the topic).

## Signal strength (per surface)
`quality = mean(0.70·relevance + 0.30·freshness)`; `volume = min(1, n/8)^0.8`; `strength = quality·(0.25 + 0.75·volume)`.
Freshness: live snapshots = 1.0, unknown date = 0.5, otherwise a half-life decay (90 d; 365 d for Scholar/Patents).
Google Trends: `0.60·level + 0.40·momentum` where level = recent index/100 and momentum = clamp(0.5 + change%/200).
Levels: high ≥ 0.65, medium ≥ 0.40, else low. **Strength is not a probability.**

## Divergence
`gap = |A − B|`; reported when gap ≥ 0.22, stronger ≥ 0.45, weaker-side confidence ≥ 0.25 and
`confidence = 0.7·min(conf) + 0.3·min(1, gap/0.5) ≥ 0.40`. Pairs without a known interpretation additionally require the weaker side to be *low* and gap ≥ 0.30.
Early-signal divergence: Trends rising ≥ 25 % while Hiring or Commercial Availability is low.

## Disagreement and claim groups
Direction (`up`/`down`) comes from the LLM when available, otherwise a transparent lexicon (`analysis/stance.py`).
A disagreement needs ≥ 2 items on each side and a minority share ≥ 25 %. Claim groups cluster statements by token overlap and
mark them *corroborated* when ≥ 2 independent sources agree.

## Blind spots
Kinds: **divergence**, **coverage** (a planned surface failed/empty → *unobserved*, not low), **temporal** (most evidence undated),
**disagreement**. Divergence importance = `0.55·gap + 0.25·stronger + 0.20·confidence`. Every blind spot lists
what could make it wrong.

## Temporal coverage
Measured only over time-bearing evidence (news, web, scholar, patents, video); live snapshots (shopping, jobs, trends) are counted separately.

## Consistency rules (v1.1)

**Surfaces vs tasks.** A *surface* is an information channel (News, Trends, Web…). A *task* is one search of a surface for one region. Every planned surface lands in exactly one bucket: *with evidence*, *empty* or *failed*; planned = with evidence + empty + failed. The same holds for tasks. `data_quality.reconciled` asserts this and is tested in all three modes.

**Trend windows.** Each mode requests a different Google Trends window (Quick 3 months, Standard 12 months, Deep 5 years) and the response records the requested window, the number of points and the real span returned. The headline change is always *last 30 days vs the 30 days before* (computed from timestamps), so modes are comparable; 90-day and 12-month horizons appear when the window is long enough. Search interest is attention, never a price direction.

**Directional evidence.** Counted three ways: items, claims and unique sources. Near-identical headlines count once; forecasts about a different horizon ("by 2030") are excluded when the question is about the near term; the lean is decided by unique sources, not headline volume, and needs ≥4 deciding sources.

**Regional comparison.** For eligible questions Standard/Deep compare Global with India (News, Trends, Web). Each region reports unique sources, up/down sources, its own trend and linked top headlines, plus whether the regions agree. This is not a worldwide country-by-country survey.

**What each mode adds.** Quick: fast first read. Standard: more sources + Global-vs-India corroboration. Deep: 8 surfaces, 20 results each, 5-year context and a research (Scholar) cross-check. Run `python scripts/compare_modes.py "<question>"` to document the differences with live data.
