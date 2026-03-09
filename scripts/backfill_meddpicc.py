#!/usr/bin/env python3
"""
One-time backfill: upgrade meddpicc_json from flat status strings to enriched
per-dimension objects {status, evidence, gap, question}.

Extracts evidence from the email body using keyword matching per MEDDPICC
dimension, maps existing discovery questions to the most relevant dimension,
and generates gap descriptions based on status.

Usage:
    python scripts/backfill_meddpicc.py          # dry-run (print only)
    python scripts/backfill_meddpicc.py --write   # commit to DB
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "triage.db"

# ── Evidence extraction patterns per dimension ────────────────────────────

# Each dimension has a list of (regex_pattern, context_window) tuples.
# We search the email body for these patterns and extract surrounding context.

DIMENSION_PATTERNS: dict[str, list[str]] = {
    "metrics": [
        r"(?i)\b(?:roi|kpi|metric|measure|benchmark|throughput|latency|accuracy|"
        r"performance|reduction|improvement|save|saving|cost|percent|%|\d+x|"
        r"volume|scale|token|request|queries|users|customers|seats|"
        r"\d+[kmb]\b|\d{2,},\d{3}|\$\d+)\b",
    ],
    "economic_buyer": [
        r"(?i)\b(?:vp|cto|ceo|cfo|coo|chief|head of|director|svp|evp|founder|"
        r"budget|approve|approval|sign.?off|authorized?|decision.?maker|"
        r"executive sponsor|board|allocated)\b",
    ],
    "decision_criteria": [
        r"(?i)\b(?:evaluat|criteria|compar|requirement|need|must have|"
        r"important|quality|reliability|security|compliance|privacy|"
        r"soc.?2|hipaa|gdpr|baa|iso|fedramp|we care about|"
        r"concern|priority|priorities|looking for|expect)\b",
    ],
    "decision_process": [
        r"(?i)\b(?:timeline|by q[1-4]|by end of|deadline|procurement|"
        r"committee|review|stage|phase|pilot|poc|proof of concept|"
        r"rollout|deploy|launch|go.?live|decision by|decide|"
        r"by (?:january|february|march|april|may|june|july|august|september|october|november|december)|"
        r"next (?:week|month|quarter))\b",
    ],
    "paper_process": [
        r"(?i)\b(?:contract|agreement|msa|nda|legal|procurement|"
        r"security review|vendor|compliance|terms|paper|sign|"
        r"purchase order|po|infosec|approved|in hand)\b",
    ],
    "implicate_pain": [
        r"(?i)\b(?:pain|problem|challenge|struggling|bottleneck|"
        r"slow|costly|manual|frustrat|inefficien|gap|limitation|"
        r"outgrown|replacing|migrat|switching from|concern|"
        r"want to|need to|looking to|trying to|we want|we need|"
        r"explore|explor|improve|increas|reduc|automat|"
        r"spend.{0,20}time|too (?:much|many|long)|hours)\b",
    ],
    "champion": [
        r"(?i)\b(?:i(?:'m| am) (?:the|a|leading|driving|responsible)|"
        r"my team|advocate|sponsor|pushing for|excited about|"
        r"passionate|i've been|we've been testing|benchmarking|"
        r"i lead|i run|i manage|i oversee|i own|our team|"
        r"i want|we're exploring|we're evaluating|we ran)\b",
    ],
    "competition": [
        r"(?i)\b(?:openai|gpt|gemini|google|mistral|cohere|llama|"
        r"competitor|alternative|bake.?off|vendor|comparison|"
        r"switch|migrat|currently using|existing provider|"
        r"head.?to.?head|vs\.?|versus)\b",
    ],
}

# Gap descriptions based on status
GAP_TEMPLATES: dict[str, dict[str, str]] = {
    "metrics": {
        "unknown": "No measurable success criteria or KPIs have been identified. Need to uncover their definition of success.",
        "partial": "Some quantitative signals mentioned but no concrete success metrics or KPIs defined yet.",
    },
    "economic_buyer": {
        "unknown": "Budget holder not identified. Don't know who controls the purse strings.",
        "partial": "Possible budget authority hinted but not confirmed. Need to verify decision-making power.",
    },
    "decision_criteria": {
        "unknown": "No clarity on what they're evaluating against. Don't know their must-haves.",
        "partial": "Some evaluation factors surfaced but full criteria not mapped. May be comparing on unstated dimensions.",
    },
    "decision_process": {
        "unknown": "No visibility into their buying process, timeline, or decision stages.",
        "partial": "Some timeline signals but full process not mapped — committee, stages, and approval chain unclear.",
    },
    "paper_process": {
        "unknown": "No mention of legal, procurement, or contract requirements. Could be a blocker later.",
        "partial": "Some procurement signals but full paper process not understood yet.",
    },
    "implicate_pain": {
        "unknown": "No business pain or driver articulated. Need to uncover what's compelling them to act.",
        "partial": "Some pain surfaced but not fully quantified or connected to business impact.",
    },
    "champion": {
        "unknown": "No internal advocate identified. Need someone on the inside pushing this forward.",
        "partial": "Possible champion but not confirmed — need to validate their influence and commitment.",
    },
    "competition": {
        "unknown": "No competitive landscape visibility. Don't know if they're evaluating other vendors.",
        "partial": "Some competitive signals but full picture unclear — may be in a multi-vendor evaluation.",
    },
}

# Question mapping keywords — to match discovery questions to dimensions
QUESTION_KEYWORDS: dict[str, list[str]] = {
    "metrics": ["metric", "kpi", "roi", "measure", "success", "throughput", "sla", "guarantee"],
    "economic_buyer": ["budget", "approval", "approve", "decision", "who else", "sponsor", "authority"],
    "decision_criteria": ["criteria", "evaluat", "requirement", "security", "compliance", "quality"],
    "decision_process": ["timeline", "process", "stage", "committee", "rollout", "pilot", "deadline", "driving the"],
    "paper_process": ["legal", "procurement", "contract", "soc2", "baa", "compliance doc", "security review", "paper"],
    "implicate_pain": ["pain", "problem", "challenge", "driving", "why now", "what happens if"],
    "champion": ["advocate", "champion", "internal", "pushing", "support"],
    "competition": ["competitor", "other vendor", "alternative", "comparing", "bake-off", "currently using"],
}


def extract_evidence(body: str, dimension: str) -> str:
    """Extract relevant sentences from email body for a given MEDDPICC dimension."""
    sentences = re.split(r'(?<=[.!?\n])\s+', body)
    evidence_parts: list[str] = []
    patterns = DIMENSION_PATTERNS.get(dimension, [])

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue
        for pattern in patterns:
            if re.search(pattern, sentence):
                # Clean up and truncate
                clean = sentence.replace("\n", " ").strip()
                if len(clean) > 200:
                    clean = clean[:197] + "..."
                if clean not in evidence_parts:
                    evidence_parts.append(clean)
                break

    # Return top 2 most relevant sentences
    return " ".join(evidence_parts[:2]) if evidence_parts else ""


def match_question_to_dimension(question: str) -> str | None:
    """Find which MEDDPICC dimension a discovery question best maps to."""
    q_lower = question.lower()
    best_dim = None
    best_score = 0

    for dim, keywords in QUESTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > best_score:
            best_score = score
            best_dim = dim

    return best_dim if best_score > 0 else None


def build_enriched_meddpicc(
    meddpicc_flat: dict[str, str],
    email_body: str,
    discovery_questions: list[str],
) -> dict[str, dict[str, str]]:
    """Build enriched MEDDPICC from existing flat data + email body."""

    # Map discovery questions to dimensions
    dim_questions: dict[str, str] = {}
    unmatched_questions: list[str] = []

    for q in discovery_questions:
        dim = match_question_to_dimension(q)
        if dim and dim not in dim_questions:
            dim_questions[dim] = q
        else:
            unmatched_questions.append(q)

    enriched: dict[str, dict[str, str]] = {}

    for dim_key, status in meddpicc_flat.items():
        # Extract evidence from email body
        evidence = ""
        if status in ("known", "partial"):
            evidence = extract_evidence(email_body, dim_key)

        # Get gap description
        gap = ""
        if status in ("unknown", "partial"):
            gap = GAP_TEMPLATES.get(dim_key, {}).get(status, "")

        # Get matched question, or pull from unmatched pool
        question = dim_questions.get(dim_key, "")
        if not question and status in ("unknown", "partial") and unmatched_questions:
            question = unmatched_questions.pop(0)

        enriched[dim_key] = {
            "status": status,
            "evidence": evidence,
            "gap": gap,
            "question": question,
        }

    return enriched


def main() -> None:
    write_mode = "--write" in sys.argv
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get all leads with their emails
    rows = conn.execute("""
        SELECT l.sender_email, l.company_name, l.meddpicc_json, l.discovery_questions_json,
               e.body, e.subject
        FROM leads l
        JOIN email_log e ON e.sender_email = l.sender_email
        ORDER BY l.score DESC
    """).fetchall()

    updates: list[tuple[str, str]] = []

    for row in rows:
        sender = row["sender_email"]
        company = row["company_name"] or sender
        meddpicc_flat = json.loads(row["meddpicc_json"])
        discovery_qs = json.loads(row["discovery_questions_json"])
        body = row["body"] or ""

        # If already enriched, extract flat statuses to re-enrich with better patterns
        first_val = next(iter(meddpicc_flat.values()), None)
        if isinstance(first_val, dict):
            meddpicc_flat = {k: v["status"] for k, v in meddpicc_flat.items()}

        enriched = build_enriched_meddpicc(meddpicc_flat, body, discovery_qs)
        enriched_json = json.dumps(enriched)
        updates.append((enriched_json, sender))

        # Print summary
        print(f"\n{'='*60}")
        print(f"  {company} ({sender})")
        print(f"{'='*60}")
        for dim_key, dim_data in enriched.items():
            status_icon = {"known": "+", "partial": "~", "unknown": "-"}[dim_data["status"]]
            print(f"  [{status_icon}] {dim_key}: {dim_data['status']}")
            if dim_data["evidence"]:
                ev = dim_data["evidence"][:80] + "..." if len(dim_data["evidence"]) > 80 else dim_data["evidence"]
                print(f"      evidence: {ev}")
            if dim_data["gap"]:
                gp = dim_data["gap"][:80] + "..." if len(dim_data["gap"]) > 80 else dim_data["gap"]
                print(f"      gap:      {gp}")
            if dim_data["question"]:
                qq = dim_data["question"][:80] + "..." if len(dim_data["question"]) > 80 else dim_data["question"]
                print(f"      ask:      {qq}")

    if not updates:
        print("\nNo leads to update.")
        conn.close()
        return

    if write_mode:
        print(f"\n>>> Writing {len(updates)} updates to {DB_PATH}...")
        for enriched_json, sender in updates:
            conn.execute(
                "UPDATE leads SET meddpicc_json = ? WHERE sender_email = ?",
                (enriched_json, sender),
            )
        conn.commit()
        print(">>> Done!")
    else:
        print(f"\n>>> DRY RUN — {len(updates)} leads would be updated.")
        print(">>> Run with --write to commit changes.")

    conn.close()


if __name__ == "__main__":
    main()
