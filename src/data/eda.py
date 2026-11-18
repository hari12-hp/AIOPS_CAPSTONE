import argparse, collections, json, statistics, time
from pathlib import Path
from src.data.common import normalise_question, read_jsonl


def empty(x):
    return not isinstance(x, str) or not x.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", default="reports/eda/report.json")
    args = parser.parse_args()
    started = time.monotonic()
    rows = list(read_jsonl(args.input))
    lengths = [len(str(r.get("solution") or "")) for r in rows]
    questions = [normalise_question(r.get("problem", "")) for r in rows]
    report = {
        "input_count": len(rows),
        "schema": sorted({k for r in rows for k in r}),
        "missing_problem": sum(empty(r.get("problem")) for r in rows),
        "missing_solution": sum(empty(r.get("solution")) for r in rows),
        "exact_duplicates": len(rows)
        - len({json.dumps(r, sort_keys=True, default=str) for r in rows}),
        "normalised_question_duplicates": len(rows) - len(set(questions)),
        "solution_chars": {
            "min": min(lengths, default=0),
            "median": statistics.median(lengths) if lengths else 0,
            "max": max(lengths, default=0),
            "over_12000": sum(n > 12000 for n in lengths),
        },
        "distributions": {},
        "seconds": time.monotonic() - started,
    }
    for field in (
        "problem_is_valid",
        "solution_is_valid",
        "problem_type",
        "question_type",
        "source",
        "synthetic",
        "answer",
    ):
        report["distributions"][field] = dict(collections.Counter(str(r.get(field)) for r in rows))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    review = []
    for row in rows[:25]:
        warnings = []
        if str(row.get("problem_is_valid")) != "Yes":
            warnings.append("problem_validity_not_yes")
        if str(row.get("solution_is_valid")) != "Yes":
            warnings.append("solution_validity_not_yes")
        if not str(row.get("answer") or "").strip() or str(row.get("answer")) == "notfound":
            warnings.append("answer_missing_or_notfound")
        review.append(
            {
                key: row.get(key)
                for key in (
                    "problem",
                    "solution",
                    "answer",
                    "problem_is_valid",
                    "solution_is_valid",
                    "source",
                    "synthetic",
                )
            }
            | {"warnings": warnings}
        )
    Path(args.output).with_name("sample_review.json").write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n"
    )


if __name__ == "__main__":
    main()
