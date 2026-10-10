# SPECTRA Frontend

Next.js/React/TypeScript investigation console for SPECTRA.

## Configuration

Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_BASE_URL` if the backend is not running at `http://localhost:8000/api`.

The frontend never receives or stores the SerpApi secret. API keys belong in the backend environment.
