# RepoMind deployment checklist

## Local verification

Run from this directory:

```bash
npm install
python -m pip install -r requirements.txt
python -m compileall api rag
npm run lint
npm run build
```

The production build should show:

- `/` as a static route

The RAG endpoint is a Python Vercel Function at `api/chat.py`, so it will not appear in the Next.js route table. Use `vercel dev` or a Vercel deployment to test the full frontend plus Python API locally.

## Required environment variables

Add these in Vercel Project Settings > Environment Variables for Production and Preview:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini
OPENAI_ROUTER_MODEL=gpt-5.4-mini
```

`OPENAI_MODEL` and `OPENAI_ROUTER_MODEL` are optional. The app defaults to `gpt-5.4-mini`, the cost-conscious GPT-5.4 variant optimized for high-volume workloads. Use `gpt-5.6-terra` (balanced) or `gpt-5.6-sol` (frontier) if you want stronger reasoning and have budget for it.

## Vercel settings

This repository stores the app in a subdirectory, so configure Vercel like this:

- Framework preset: Next.js
- Root Directory: `repomind`
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: leave default
- Node.js version: 20 or newer
- Python version: 3.12 or newer, from `pyproject.toml`

After deployment, test these questions:

1. `Why did we switch the payment service from an in-memory cache to Redis?`
2. `Is there a reason the retry logic in api_client.py uses exponential backoff?`
3. `What's the current best practice for rate limiting in FastAPI?`

The first should cite internal sources, the second should decline to invent rationale, and the third should be marked as external knowledge.
