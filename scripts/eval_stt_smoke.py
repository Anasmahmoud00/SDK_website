#!/usr/bin/env python3
"""Small STT smoke evaluator with built-in WER calculation.

Input CSV format:
audio_path,reference_text,hypothesis_text

If hypothesis_text is empty, this script currently marks it as missing.
This keeps the script dependency-light and useful for quick defense evidence.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RowResult:
    audio_path: str
    ref_words: int
    edit_distance: int
    wer: float


def _levenshtein(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[m][n]


def _wer(reference: str, hypothesis: str) -> tuple[int, int, float]:
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0, 0, 0.0
    distance = _levenshtein(ref_words, hyp_words)
    return len(ref_words), distance, distance / len(ref_words)


def evaluate(csv_path: Path) -> int:
    if not csv_path.exists():
        print(f"Input CSV not found: {csv_path}")
        return 2

    results: list[RowResult] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"audio_path", "reference_text", "hypothesis_text"}
        if not required.issubset(reader.fieldnames or set()):
            print("CSV must contain columns: audio_path, reference_text, hypothesis_text")
            return 2

        for row in reader:
            ref = (row.get("reference_text") or "").strip()
            hyp = (row.get("hypothesis_text") or "").strip()
            audio = (row.get("audio_path") or "").strip()
            ref_len, dist, wer_value = _wer(ref, hyp)
            results.append(RowResult(audio, ref_len, dist, wer_value))

    if not results:
        print("No rows found.")
        return 1

    total_ref = sum(r.ref_words for r in results)
    total_dist = sum(r.edit_distance for r in results)
    corpus_wer = (total_dist / total_ref) if total_ref else 0.0

    print("STT Smoke Evaluation")
    print("===================")
    print(f"Rows: {len(results)}")
    print(f"Corpus WER: {corpus_wer:.4f} ({corpus_wer * 100:.2f}%)")
    print("")
    print("Per-row:")
    for r in results:
        print(f"- {r.audio_path or '<no-audio>'}: WER={r.wer:.4f} ({r.wer * 100:.2f}%)")

    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/eval_stt_smoke.py <csv_file>")
        return 2
    return evaluate(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
