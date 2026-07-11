# Synthetic Dataset — Northwind Analytics (fictional company)

This is a synthetic but internally-consistent dataset standing in for a real engineering team's artifacts, so you can build and evaluate the RepoMind prototype without configuring GitHub/Slack/email API access.

## Files

| File | Mimics | Contents |
|---|---|---|
| `commits.json` | GitHub commit API objects | 15 commits, includes 2 deliberately undocumented ones (`c3d4e5f`, `o5p6q7r`) to test the "no rationale found" guardrail |
| `pull_requests.json` | GitHub PR API objects | 8 PRs with descriptions + review comment threads, including one with genuine reviewer pushback (PR #190) |
| `tickets.json` | Jira/Linear API objects | 7 tickets, cross-referenced by ID in commits/PRs |
| `chat_messages.json` | Slack API message objects | 16 messages across 5 threads/channels, cross-referenced by topic |
| `emails.json` | Email objects | 2 leadership-summary emails referencing the same decisions from other angles |
| `docs.json` | Internal RFC docs + project proposal | 1 project proposal (`PROP-001`, Jan 2025) plus 2 RFCs (RFC-004: orders datastore, RFC-007: monolith split) |
| `ground_truth_eval.json` | — | Maps the 8 seed questions from Task 1 to expected source citations and expected answer summaries — use this directly as your Task 5 eval harness's ground truth |

## The project proposal (`PROP-001`) ties everything together

Dated Jan 15, 2025 — before any of the other artifacts — `PROP-001` is the originating document that predicts and authorizes every decision thread in the dataset:
- Flags payment caching as a known risk **before** the Nov 2025 incident that actually triggered PAY-102/PR#245
- Calls for an orders-datastore RFC **before** RFC-004/ORD-58 existed
- Proposes phased auth modernization **before** SEC-33's three phases shipped
- Proposes phased monolith decomposition **before** RFC-007/ARCH-12 formalized it

This gives you a top-level "why did we even start this" artifact to test against questions like *"what was the original business case for splitting the monolith?"* — the answer should trace back through RFC-007 to the broader velocity/scaling rationale in PROP-001, which is a good test of whether your system can chain reasoning across more than one hop rather than just returning the nearest single document.

## Design choices worth knowing

- **Cross-referencing is real, not decorative.** Ticket IDs, PR numbers, and thread IDs in one file genuinely appear in others (e.g. `PAY-102` appears in the ticket, the PR, the commit message, the Slack thread, and the email). This lets you actually test graph-linking logic, not just vector search over isolated blobs.
- **Two intentionally undocumented commits** exist specifically so you can demonstrate your confidence-check/guardrail correctly declining to answer rather than hallucinating a plausible-sounding rationale.
- **One question (rate limiting best practice) has zero internal sources on purpose** — this is your test case for the external-search-tool fallback path, not a gap in the data.
- **7 decision "threads" span the 8 seed evaluation questions** from your Task 1 documentation, so you can plug `ground_truth_eval.json` straight into your Task 5 RAGAS/LLM-as-judge harness.

## How to use this

1. Treat each `.json` file as if it were the response body from the real API it mimics. Write your ingestion/chunking code against these files first.
2. When you're ready to connect real data later, you should only need to swap the *source* of these objects (an actual GitHub/Slack/Jira API call) — the object shape was designed to match the real APIs closely enough that your parsing/chunking logic shouldn't need to change much.
3. Feed `ground_truth_eval.json`'s questions into your prototype once built, and compare its citations/answers against the `expected_sources` / `expected_answer_summary` fields for your Task 5 write-up.

## Extending the dataset

If you want more volume (e.g. to stress-test retrieval at scale), the easiest path is asking an LLM to generate additional commits/PRs/tickets *within the same fictional decision threads* above (e.g. more auth-service follow-up commits, more monolith-split phases) rather than inventing unrelated threads — this keeps the cross-referencing coherent as the dataset grows.
