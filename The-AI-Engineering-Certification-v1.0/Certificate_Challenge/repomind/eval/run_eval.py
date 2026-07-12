"""
RepoMind Evaluation Harness
===========================

Runs RAGAS + LLM-as-Judge evaluation against the 30 ground-truth Q/A pairs in
data/ground_truth_eval.json.

Usage
-----
    cd repomind
    python -m eval.run_eval
    REPOMIND_RETRIEVAL_MODE=dense python -m eval.run_eval   # dense-vector-only baseline (Task 6.2)

Prerequisites
-------------
    Install eval/requirements-eval.txt in a SEPARATE virtualenv from the
    runtime's requirements.txt (ragas pulls langchain-openai, which pins
    openai<2.0.0 and conflicts with the runtime's openai==2.15.0).
    Set OPENAI_API_KEY in your environment (or .env.local for vercel dev).

Output
------
    eval/results_<timestamp>.json   — per-question scores + aggregate metrics
    Summary table printed to stdout
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so `rag` is importable
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Load .env.local if present (for local dev without vercel dev)
_env_file = Path(_ROOT) / ".env.local"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from rag.agent import AI_GATEWAY_BASE_URL, retrieval_mode, run_agent
from rag.embeddings import vector_search
from rag.knowledge_base import build_knowledge_base
from rag.retrieval import search as bm25_search

GROUND_TRUTH_FILE = Path(_ROOT) / "data" / "ground_truth_eval.json"
RESULTS_DIR = Path(_ROOT) / "eval"
RESULTS_DIR.mkdir(exist_ok=True)

_JUDGE_MODEL = os.getenv("OPENAI_MODEL") or "openai/gpt-4o-mini"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_ground_truth() -> list[dict[str, Any]]:
    with GROUND_TRUTH_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _retrieve_context(question: str) -> list[str]:
    """
    Return text of top-8 chunks (used as RAGAS context). Honors
    REPOMIND_RETRIEVAL_MODE so a dense-only eval run (Task 6.2 baseline) gets
    dense-only context, not hybrid context — otherwise RAGAS would be scoring
    the agent's dense-only answer against hybrid retrieval's context.
    """
    kb = build_knowledge_base()
    try:
        dense = vector_search(question, top_k=8)
    except Exception:
        dense = []

    if retrieval_mode() == "dense":
        return [c.text for c in dense[:8]]

    sparse = bm25_search(question, kb, top_k=8)

    seen: set[str] = set()
    texts: list[str] = []
    for chunk in dense + sparse:
        if chunk.id not in seen:
            seen.add(chunk.id)
            texts.append(chunk.text)
    return texts[:8]


# ── RAGAS evaluation ──────────────────────────────────────────────────────────

def run_ragas_eval(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> tuple[dict[str, float], list[dict[str, float]]]:
    """
    Run RAGAS faithfulness + context_precision + context_recall.

    Returns (aggregate, per_question):
      aggregate    — dict metric -> mean score (0-1), or {} if ragas unavailable/failed
      per_question — list of per-question {metric: score} dicts, same order as
                     `questions`, or [] alongside an empty aggregate.

    ragas 0.2.6's EvaluationResult.__getitem__ returns a per-row list, not the
    aggregate — e.g. result["faithfulness"] == [0.83, 1.0, ...], one entry per
    row, not a scalar. float(result["faithfulness"]) raises TypeError. Reading
    via .to_pandas() gives both the per-row values (for qualitative
    failure analysis) and something we can safely average ourselves for the
    aggregate, without depending on an internal aggregate-access API that
    isn't part of ragas's public surface.
    """
    try:
        from datasets import Dataset  # type: ignore[import]
        from ragas import evaluate  # type: ignore[import]
        from ragas.metrics import (  # type: ignore[import]
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as e:
        print(f"[RAGAS] Skipping — import error: {e}")
        return {}, []

    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)
    metric_names = ["faithfulness", "context_precision", "context_recall"]
    try:
        result = evaluate(dataset, metrics=[faithfulness, context_precision, context_recall])
        df = result.to_pandas()

        per_question: list[dict[str, float]] = []
        for _, row in df.iterrows():
            per_question.append({m: (None if row[m] != row[m] else float(row[m])) for m in metric_names})

        aggregate: dict[str, float] = {}
        for m in metric_names:
            vals = [v for v in df[m].tolist() if v == v]  # drop NaN
            aggregate[m] = round(sum(vals) / len(vals), 4) if vals else 0.0

        return aggregate, per_question
    except Exception as e:
        print(f"[RAGAS] Evaluation failed: {e}")
        return {}, []


# ── LLM-as-Judge ─────────────────────────────────────────────────────────────

def llm_judge_score(
    question: str,
    answer: str,
    expected_summary: str,
    sources: list[str],
    expected_sources: list[str],
) -> dict[str, Any]:
    """
    Ask the LLM to score the answer on three dimensions (0–10 each):
      (a) correctness  — accuracy of cited rationale (or correct refusal for negative cases)
      (b) hallucination_guard — no fabrication; correctly says "no rationale" when appropriate
      (c) usefulness   — how useful to a practising engineer
    Returns dict with integer scores and a brief justification string.
    """
    from openai import OpenAI

    # This custom judge is our own tooling, so it goes through AI Gateway like
    # the rest of the app. RAGAS's own internal metric LLM calls (above, in
    # run_ragas_eval) are third-party library plumbing and are left on direct
    # OPENAI_API_KEY access rather than reconfigured — out of scope here.
    gateway_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_OIDC_TOKEN")
    client = OpenAI(api_key=gateway_key, base_url=AI_GATEWAY_BASE_URL)
    is_negative = not expected_sources

    prompt = f"""You are an expert evaluator for an engineering knowledge assistant.

Question: {question}

Expected answer summary: {expected_summary}

Actual answer: {answer}

Sources cited by the system: {sources}
Expected sources: {expected_sources}
Is this a negative-control case (correct answer = "no rationale found"): {is_negative}

Score from 0 to 10 on each dimension. Return JSON only with these exact keys:
  "correctness": int          (accuracy of cited rationale; 10 for correct refusal on negative cases)
  "hallucination_guard": int  (10 = no hallucination and correctly declines negative cases)
  "usefulness": int           (how useful to a practising engineer)
  "justification": str        (≤2 sentences explaining the scores)
"""

    try:
        resp = client.chat.completions.create(
            model=_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            # AI Gateway rejects OpenAI's plain {"type": "json_object"} shorthand
            # with a 400 ("Invalid input") — it requires the full json_schema
            # format instead (verified against the gateway directly).
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "judge_score",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "correctness": {"type": "integer"},
                            "hallucination_guard": {"type": "integer"},
                            "usefulness": {"type": "integer"},
                            "justification": {"type": "string"},
                        },
                        "required": [
                            "correctness",
                            "hallucination_guard",
                            "usefulness",
                            "justification",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            max_completion_tokens=300,
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        print(f"  [Judge] Error: {e}")
        return {
            "correctness": 0,
            "hallucination_guard": 0,
            "usefulness": 0,
            "justification": f"error: {e}",
        }


# ── Main harness ──────────────────────────────────────────────────────────────

def main() -> None:
    # AI_GATEWAY_API_KEY (or VERCEL_OIDC_TOKEN) drives run_agent() and the
    # custom LLM-judge; OPENAI_API_KEY drives RAGAS's own internal metric
    # calls (see llm_judge_score's docstring note) — both are required here.
    if not (os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_OIDC_TOKEN")):
        print("ERROR: AI_GATEWAY_API_KEY is not set. Add it to .env.local or your shell.")
        sys.exit(1)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-..."):
        print("ERROR: OPENAI_API_KEY is not set (required by RAGAS's internal metric calls). Add it to .env.local or your shell.")
        sys.exit(1)

    gt_items = _load_ground_truth()
    print(f"Loaded {len(gt_items)} ground-truth items.")
    print(f"Judge model: {_JUDGE_MODEL}\n")

    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    ground_truths: list[str] = []
    per_question_results: list[dict[str, Any]] = []

    for i, item in enumerate(gt_items, 1):
        q: str = item["question"]
        expected_summary: str = item["expected_answer_summary"]
        expected_sources: list[str] = item.get("expected_sources", [])

        print(f"[{i}/{len(gt_items)}] {q[:72]}...")
        t0 = time.time()
        try:
            result = run_agent(q)
        except Exception as e:
            print(f"  Agent error: {e}")
            result = {"answer": "", "sources": [], "confidence": "error", "queryType": "error"}
        elapsed = time.time() - t0

        answer_text: str = result.get("answer", "")
        sources: list[str] = result.get("sources", [])
        ctx = _retrieve_context(q)

        questions.append(q)
        answers.append(answer_text)
        contexts.append(ctx)
        ground_truths.append(expected_summary)

        print(f"   {elapsed:.1f}s | confidence={result.get('confidence')} | sources={sources}")

        judge = llm_judge_score(q, answer_text, expected_summary, sources, expected_sources)
        print(
            f"   Judge → correctness={judge.get('correctness')} "
            f"hallucination_guard={judge.get('hallucination_guard')} "
            f"usefulness={judge.get('usefulness')}"
        )

        per_question_results.append({
            "question": q,
            "answer": answer_text,
            "sources": sources,
            "expected_sources": expected_sources,
            "confidence": result.get("confidence"),
            "query_type": result.get("queryType"),
            "elapsed_s": round(elapsed, 2),
            "judge_correctness": judge.get("correctness"),
            "judge_hallucination_guard": judge.get("hallucination_guard"),
            "judge_usefulness": judge.get("usefulness"),
            "judge_justification": judge.get("justification"),
        })

    # ── RAGAS ─────────────────────────────────────────────────────────────
    print("\nRunning RAGAS metrics (may take a few minutes for 30 questions)...")
    ragas_scores, ragas_per_question = run_ragas_eval(questions, answers, contexts, ground_truths)

    for row, ragas_row in zip(per_question_results, ragas_per_question or [{}] * len(per_question_results)):
        row["ragas_faithfulness"] = ragas_row.get("faithfulness")
        row["ragas_context_precision"] = ragas_row.get("context_precision")
        row["ragas_context_recall"] = ragas_row.get("context_recall")

    # ── Aggregates ────────────────────────────────────────────────────────
    def avg(key: str) -> float:
        vals = [r[key] for r in per_question_results if isinstance(r.get(key), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    mode = retrieval_mode()
    summary = {
        "retrieval_mode": mode,
        "n_questions": len(gt_items),
        "ragas": ragas_scores,
        "llm_judge": {
            "avg_correctness": avg("judge_correctness"),
            "avg_hallucination_guard": avg("judge_hallucination_guard"),
            "avg_usefulness": avg("judge_usefulness"),
        },
        "per_question": per_question_results,
    }

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"results_{mode}_{ts}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ── Print summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RAGAS Metrics")
    print("=" * 60)
    if ragas_scores:
        for k, v in ragas_scores.items():
            print(f"  {k:<28} {v:.3f}")
    else:
        print("  (skipped — ragas not available or failed)")

    print("\nLLM-as-Judge Averages  (out of 10)")
    print("=" * 60)
    for k, v in summary["llm_judge"].items():
        print(f"  {k:<32} {v:.1f}")

    print(f"\nFull results saved → {out_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
