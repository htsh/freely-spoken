#!/usr/bin/env python3
"""Compare two labeled eval outputs side by side.

Aligns two label_catalog.py outputs by passage id and surfaces where the two
models disagree — especially on the high-risk passages, where tone/safety
judgment is what actually decides the winner. JSON validity and vocab
compliance are already guaranteed by constrained decoding, so this focuses on
judgment, not format.

Usage:
    python compare_evals.py outputs/eval.A.json outputs/eval.B.json \\
        --sample eval_sample.json
"""

from __future__ import annotations

import argparse
import json
import os

LIST_FIELDS = ("themes", "useWhen", "emotionalFit", "avoidWhen",
               "vulnerableStatesToAvoid")


def load_rows(path):
    data = json.load(open(path, encoding="utf-8"))
    rows = data["rows"] if isinstance(data, dict) and "rows" in data else data
    model = data.get("model", os.path.basename(path)) if isinstance(data, dict) else path
    return model, {r["id"]: r for r in rows}


def load_report(path):
    rp = path + ".report.json"
    return json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None


def jaccard(a, b):
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def focus_ids(sample_path):
    if not sample_path or not os.path.exists(sample_path):
        return set()
    cov = json.load(open(sample_path, encoding="utf-8")).get("coverage", {})
    ids = set()
    for key, vals in cov.items():
        if "HIGH-RISK" in key:
            ids.update(vals)
    return ids


def fmt(v):
    if isinstance(v, list):
        return "[" + ", ".join(v) + "]" if v else "[]"
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file_a")
    ap.add_argument("file_b")
    ap.add_argument("--sample", default="eval_sample.json")
    args = ap.parse_args(argv)

    model_a, A = load_rows(args.file_a)
    model_b, B = load_rows(args.file_b)
    shared = sorted(set(A) & set(B))
    focus = focus_ids(args.sample)

    print(f"A = {model_a}")
    print(f"B = {model_b}")
    print(f"shared passages: {len(shared)}\n")

    for path, tag in ((args.file_a, "A"), (args.file_b, "B")):
        rep = load_report(path)
        if rep:
            print(f"[{tag}] labeled {rep.get('rowsLabeled')}/{rep.get('rowsAttempted')}, "
                  f"json_failures={rep.get('json_failures')}, "
                  f"vocab_failures={rep.get('vocab_failures')}, "
                  f"avg_latency={rep.get('avg_latency_s')}s, structured={rep.get('structured')}")
    print()

    # --- agreement metrics ---
    tone_match = sum(1 for i in shared if A[i].get("tone") == B[i].get("tone"))
    print("=== agreement across shared passages ===")
    print(f"tone exact match: {tone_match}/{len(shared)} "
          f"({round(100*tone_match/len(shared)) if shared else 0}%)")
    for f in LIST_FIELDS:
        avg = sum(jaccard(A[i].get(f), B[i].get(f)) for i in shared) / len(shared) if shared else 0
        print(f"{f} avg Jaccard: {avg:.2f}")

    # --- high-risk side by side ---
    if focus:
        print("\n=== HIGH-RISK passages (decide the winner here) ===")
        for i in sorted(focus):
            if i not in A or i not in B:
                continue
            ref = A[i].get("passageRef", i)
            print(f"\n{i}  {ref}")
            for f in ("tone", "themes", "avoidWhen", "vulnerableStatesToAvoid"):
                va, vb = fmt(A[i].get(f)), fmt(B[i].get(f))
                flag = "  <-- DIFFERS" if A[i].get(f) != B[i].get(f) else ""
                print(f"    {f:24} A: {va}")
                print(f"    {'':24} B: {vb}{flag}")

    # --- tone disagreements (the rows a human must adjudicate) ---
    disagree = [i for i in shared if A[i].get("tone") != B[i].get("tone")]
    if disagree:
        print(f"\n=== tone disagreements ({len(disagree)}) — human review ===")
        for i in disagree:
            print(f"  {i} {A[i].get('passageRef','')}: "
                  f"A={A[i].get('tone')}  B={B[i].get('tone')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
