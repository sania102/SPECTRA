# SPECTRA Setup Guide

This is the complete local setup path for a fresh machine.

## 1. Install prerequisites

Install:

- Python 3.11 or newer
- Node.js 20 or newer
- npm

Verify:

```bash
python --version
node --version
npm --version
```

## 2. Create the backend environment

From the SPECTRA root:

```bash
python -m venv .venv
```

Activate it.

Windows:

```bash
.venv\\Scripts\\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r backend/requirements.txt
```

## 3. Configure `.env`

Copy the root `.env.example` to `.env`.

At minimum for live investigations:

```text
SERPAPI_API_KEY=your_serpapi_key
```

Optional LLM enrichment:

```text
LLM_API_KEY=your_openai_key
LLM_MODEL=gpt-6-luna
```

Do not commit `.env`.

## 4. Start the backend

From the SPECTRA root:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Verify:

```text
http://localhost:8000/health
```

For live mode, readiness should report SerpApi as configured:

```text
http://localhost:8000/api/readiness
```

## 5. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## 6. First run: use Demo Mode

Before spending time troubleshooting external APIs, click **Launch demo investigation**.

This proves the backend/frontend connection and demonstrates the full UX without SerpApi or an LLM key.

## 7. First live investigation

After Demo Mode works, enter a question such as:

```text
Is humanoid robotics actually commercially mature?
```

Choose **Standard** depth and run the investigation.

## 8. Common issues

### `503` on a live investigation

Check `SERPAPI_API_KEY` and restart the backend after changing `.env`.

### Frontend cannot reach backend

Make sure the backend is running on port 8000 and that the frontend is using the expected API origin.

### LLM is unavailable

This is allowed. SPECTRA is designed to run its deterministic analysis without LLM enrichment.

### `npm install` is slow

Wait for the package installation to complete; the frontend build depends on it. The repository's own code does not require a global Next.js installation.
