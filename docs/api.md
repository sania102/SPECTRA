# SPECTRA API

## `GET /health`

Basic process health.

Example:

```json
{"status":"ok","service":"spectra-backend","version":"0.3.0"}
```

## `GET /api/status`

Returns application and provider configuration state without exposing secrets.

## `GET /api/readiness`

Reports whether required live-search configuration is present.

- `200` when required SerpApi configuration is present.
- `503` when live-search configuration is missing.

## `GET /api/investigations/demo`

Returns a deterministic demo investigation. No external provider is called.

## `POST /api/investigations`

Request:

```json
{
  "question": "Is humanoid robotics actually commercially mature?",
  "depth": "standard"
}
```

`depth` can be `quick`, `standard`, or `deep`.

The response contains the investigation plan, signals, divergences, potential blind spots, evidence, provenance, advanced contextual analysis, and execution metadata.

## Error contract

Validation errors return `422` with:

```json
{
  "error": "validation_error",
  "detail": "The investigation request is invalid.",
  "request_id": "...",
  "fields": []
}
```

Provider configuration failures return `503`; provider request failures return `502`; unexpected backend failures return a safe `500` response with a request ID.

## Request tracing

Every response includes:

- `X-Request-ID`
- `X-Process-Time-Ms`

A caller can provide its own `X-Request-ID`; otherwise SPECTRA generates one.
