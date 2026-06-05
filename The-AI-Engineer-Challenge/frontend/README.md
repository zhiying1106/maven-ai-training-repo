# Mindful Coach — Frontend

Next.js chat UI for the FastAPI mental coach backend (`/api/chat`).

## Prerequisites

- [Node.js](https://nodejs.org/) 18+ (includes `npm`)
- Backend running with `OPENAI_API_KEY` set (see `../api/README.md`)

## Quick start (local)

**Terminal 1 — backend** (from repo root):

```bash
uv sync
# PowerShell:
$env:OPENAI_API_KEY = "sk-your-key-here"
uv run uvicorn api.index:app --reload
```

**Terminal 2 — frontend** (from this folder):

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

By default, the dev server **proxies** `/api/*` to `http://localhost:8000`, so you do not need a `.env.local` file for local testing.

### Optional environment variable

Copy `.env.local.example` to `.env.local` if you want to call the backend directly:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

| Command        | Description              |
|----------------|--------------------------|
| `npm run dev`  | Dev server on port 3000  |
| `npm run build`| Production build         |
| `npm run start`| Run production build     |
| `npm run lint` | ESLint                   |

## Deploying on Vercel

1. Deploy from the repo root with Vercel CLI (`vercel`) or connect the GitHub repo.
2. Set the **Root Directory** to `frontend` for the Next.js app, or use a monorepo setup.
3. Add `OPENAI_API_KEY` in the Vercel project environment variables for the Python API.
4. When frontend and API share the same domain, leave `NEXT_PUBLIC_API_URL` unset so requests go to `/api/chat` on the same host.

## Design notes

- Dark slate theme with teal accents for strong contrast (no light-on-light text).
- Message bubbles grow with content; chat area scrolls independently.
- Starter prompts help users begin a session quickly.
