

# Session 12: Production Agent Patterns - Guardrails, Caching, and A2A

### [Quicklinks](https://github.com/AI-Maker-Space/The-AI-Engineering-Certification-v1.0/tree/main/00_Docs/Modules)


| 📰 Session Sheet                      | ⏺️ Recording | 🖼️ Slides | 👨‍💻 Repo    | 📝 Homework | 📁 Feedback |
| ------------------------------------- | ------------ | ---------- | ------------- | ----------- | ----------- |
| [Session 12: Production 101: Guardrails & Caching](https://github.com/AI-Maker-Space/The-AI-Engineering-Certification-v1.0/tree/main/00_Docs/Modules/12_Production) |[Recording!](https://us02web.zoom.us/rec/share/Yx3VqEBLbCZAXsjTL1L98NupP5hfadVQUYIvV3BX94edcmkRJAKczcUAKZ0NMGtQ.aDpXtTci_YW4ovbs) <br> passcode: `6JWfF%r&`| [Session 12 Slides](https://canva.link/mu8p2oni7jylf95) |You are here! | [Optional Session 12 Assignment](https://forms.gle/PVMnzonTDGoaNwZ48) | [Feedback 7/9](https://forms.gle/NVyhkaEERgB9zhGQ7) |




## Main Assignment

Previous sessions built, evaluated, and served the cat health agent. Session 12 prepares it for production with three small, self-contained concepts:

```text
01 Guardrails -> control what goes into and comes out of the agent   (notebook)
02 Caching    -> stop paying for the same answer twice               (notebook)
a2a/          -> let your agent talk to other agents over a protocol (runnable mini-project)
```

Each part is deliberately short: one new concept and a handful of tasks. The parts are independent — there is no set order or outline for this session. Pick whichever interests you most, or work through all three.

## The Parts

**`01_Cat_Health_Agent_Guardrails.ipynb`** — Build layered guardrails around the agent: deterministic input rails (emergency escalation, injection blocking, PII redaction), a model-based topical guard, and output rails that check and repair draft replies, wired into the agent loop with LangChain middleware.

**`02_Cat_Health_Agent_Caching.ipynb`** — Stop paying for repeated work: exact-match response caching, a from-scratch semantic cache (and why it is dangerous in a health domain), embedding and tool-result caches, and provider-side prompt caching you can measure in the usage details.

**`a2a/`** — Build the A2A protocol from the wire up: a specialist agent behind a minimal A2A server (`server.py`), a discovery-driven client (`client.py`), and a front-desk agent that delegates across the protocol (`front_desk.py`). Start with [`a2a/README.md`](a2a/README.md) — it walks through starting the server and testing it with curl, the client, the delegation demo, and a no-API-key smoke test.

## Setup

From this folder, install the environment with uv:

```bash
uv sync
```

Then open the notebooks in Cursor or VS Code and select the Python/Jupyter environment created by uv.

You will need an OpenAI API key available when running the notebooks:

```bash
export OPENAI_API_KEY="your-key"
```

Optional LangSmith tracing:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="your-key"
```

The `a2a/` mini-project starts a local HTTP server on port 9999. Nothing leaves your machine; stop it with `Ctrl+C`.

## Questions

### ❓ Question #1

In `01_Cat_Health_Agent_Guardrails.ipynb`, input rails run in a specific order: deterministic checks (emergency, injection, PII) first, then the model-based topical guard. Why is that ordering important in production — and why do the rails return decisions like `escalate`, `block`, and `rewrite` instead of a simple boolean pass/fail?

#### ✅ Answer
- Cost and latency — the deterministic checks (regex/pattern matches for emergency, injection, PII) are free and instant, while the topical guard is a model call. Ordering cheap-and-fast before expensive-and-slow means most requests are filtered before you ever pay for a model round-trip.
- Fail-safe short-circuiting — emergency and injection matches must escalate/block immediately, before any model involvement, so a prompt-injection attempt or a "my cat is seizing" message never even reaches the LLM where it could be reasoned about, argued with, or (in the injection case) followed.
- PII must be scrubbed before the topical guard runs — since the topical guard is itself a model call, any PII in the input would otherwise be sent to that model too. Redacting first means contact details never appear in any model context, logs, or traces, no matter which rail sees the text next.
- Boolean pass/fail can't express what needs to happen next — a true/false verdict tells you that something's wrong but not what to do about it. block (refuse safely), escalate (short-circuit to an urgent redirect), and rewrite (repair and continue) are three different control-flow branches, and only rewrite should let execution proceed to the model.
- Emergency handling isn't a safety block, it's a routing decision — a cat mid-seizure doesn't need refusal, it needs redirection to a vet now. Collapsing that into "fail" would either wrongly block a legitimate, urgent user or wrongly let it through to get a leisurely chatbot answer — escalate is a distinct outcome because the right response isn't "no," it's "not here."

### ❓ Question #2

In `02_Cat_Health_Agent_Caching.ipynb`, a semantic cache can serve a paraphrased FAQ for the price of one embedding call — but the notebook also shows how a one-word difference (treat vs. poison) can produce a catastrophic cache hit. Why can't you fix this with a better similarity threshold alone, and what should a production health agent do instead for high-stakes queries?

#### ✅ Answer
- Embeddings measure surface similarity, not stakes — cosine similarity captures "these sentences look alike," not "the consequences of confusing them are catastrophic." A poisoning question and a feeding question can legitimately sit close together in embedding space because they share almost all their words and structure.
- Any single threshold has a counterexample — push the threshold up to separate chocolate-poisoning from chicken-treats, and you lose real paraphrases elsewhere; leave it lower and some critically different pair (like this one) will always sit just above the cutoff. There's no value that makes similarity and safety coincide for every query.
- A cache hit is presented with false confidence — a bad cache hit doesn't just risk being wrong, it's wrong faster and more confidently than a live model call would have been, since there's no generation step where the model might notice the danger.
- The fix is routing, not tuning — high-stakes queries must bypass the cache entirely rather than be filtered by similarity score. The notebook reuses the deterministic emergency rail from notebook 1: if run_input_rails returns escalate, the query never consults or populates the semantic cache.
- Guardrails and caching aren't separate systems — the rails are what decide what's safe to cache in the first place. A production agent should treat "is this cacheable" as a guardrail decision made before the cache layer, not a property inferred from the query's embedding.

## Submitting Your Homework

Follow these steps to prepare and submit your homework:

1. Pull the latest updates from upstream into the main branch of your AIE9 repo:

```bash
git checkout main
git pull upstream main
git push origin main
```

1. Start Cursor from the `12_Production_Agent_Patterns` folder.
2. Work through the parts you chose (notebooks and/or the `a2a/` mini-project).
3. Keep useful outputs that help explain your work — for example guardrail decision tables, cache hit/miss timings, or the A2A delegation trace. Remove secrets and excessively noisy outputs.
4. Add, commit, and push your modified work to your origin repository.

When submitting your homework, provide the GitHub URL to your AIE9 repo.
