import csv
import re
from pathlib import Path
from time import perf_counter
from campusmitra.config import BASE_DIR
from campusmitra.rag import answer_question

def tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

def run_evaluation(store):
    path = BASE_DIR / "evaluation" / "test_questions.csv"
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    if not rows:
        return {"total": 0, "message": "No evaluation questions found."}
    results = []
    correct = grounded = total_time = 0
    for row in rows:
        started = perf_counter()
        response = answer_question(row["question"], store)
        elapsed = perf_counter() - started
        expected = tokens(row["expected_answer"])
        actual = tokens(response["answer"])
        overlap = len(expected & actual) / max(1, len(expected))
        is_grounded = bool(response.get("sources")) and response.get("grounded", False)
        # Lexical coverage is a simple project-level proxy, not a human correctness judgment.
        is_correct_proxy = overlap >= 0.35
        correct += int(is_correct_proxy)
        grounded += int(is_grounded)
        total_time += elapsed
        results.append({
            "question": row["question"],
            "expected_answer": row["expected_answer"],
            "answer": response["answer"],
            "keyword_coverage": round(overlap, 3),
            "correctness_proxy": is_correct_proxy,
            "grounded": is_grounded,
            "response_time_seconds": round(elapsed, 3),
            "sources": [s["filename"] for s in response.get("sources", [])]
        })
    n = len(rows)
    return {
        "total": n,
        "correctness_proxy_percent": round(correct / n * 100, 1),
        "grounded_response_percent": round(grounded / n * 100, 1),
        "average_response_time_seconds": round(total_time / n, 3),
        "method_note": "Correctness is estimated using expected-answer keyword coverage. "
                       "Manually review answers before reporting academic accuracy.",
        "results": results
    }
