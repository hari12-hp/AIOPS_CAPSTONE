"""Record real Compose/API/model/exporter checks for the submission report."""

import json
from pathlib import Path
import time
import re
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def get(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    with urlopen(
        Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=190
    ) as response:
        text = response.read().decode()
        try:
            return json.loads(text)
        except ValueError:
            return text


def main():
    checks = []

    def check(name, condition, detail):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    health = get("http://localhost:8000/health")
    check(
        "FastAPI health",
        health["status"] == "ok" and health["inference_engine"] == "mlflow",
        health,
    )
    for name, question, expected in [
        ("Algebra", "Solve 2x + 3 = 11 for x. Give only the final value.", "4"),
        ("Fractions", "What is 3/4 plus 1/8? Give only the simplified fraction.", "7/8"),
    ]:
        result = get("http://localhost:8080/v1/solve", {"question": question})
        answer = result["answer"].replace(" ", "")
        check(
            f"Nginx → FastAPI → MLflow: {name}",
            expected in answer or (expected == "7/8" and "\\frac{7}{8}" in answer),
            result,
        )
    check("MLflow tracking health", get("http://localhost:5000/health") == "OK", "HTTP 200")
    check(
        "MLflow registered serving health",
        get("http://localhost:5002/ping") in ("", "\n", {}),
        "HTTP 200",
    )
    dashboard = get("http://localhost:13000/api/dashboards/uid/local-math-assistant")
    check(
        "Grafana provisioned dashboard",
        len(dashboard["dashboard"]["panels"]) >= 8,
        dashboard["dashboard"]["title"],
    )
    target_data = get("http://localhost:19090/api/v1/targets")["data"]["activeTargets"]
    targets = {target["labels"]["job"]: target["health"] for target in target_data}
    check(
        "Prometheus exporters",
        all(
            targets.get(job) == "up"
            for job in ["math-assistant", "math-model", "prometheus", "grafana"]
        ),
        targets,
    )
    query = get(
        "http://localhost:19090/api/v1/query?"
        + urlencode({"query": "math_model_predictions_total"})
    )
    for _ in range(3):
        if any(float(row["value"][1]) > 0 for row in query["data"]["result"]):
            break
        time.sleep(5)
        query = get(
            "http://localhost:19090/api/v1/query?"
            + urlencode({"query": "math_model_predictions_total"})
        )
    check(
        "Live model generation metric",
        any(float(row["value"][1]) > 0 for row in query["data"]["result"]),
        query["data"]["result"],
    )
    partitions = {}
    for name in ("train", "validation", "test"):
        rows = [
            json.loads(line)
            for line in Path(f"data/splits/{name}.jsonl").read_text().splitlines()
            if line.strip()
        ]
        partitions[name] = {re.sub(r"\s+", " ", row["problem"].strip()).casefold() for row in rows}
    disjoint = all(
        not partitions[a] & partitions[b]
        for a, b in [("train", "test"), ("train", "validation"), ("test", "validation")]
    )
    check(
        "Question partitions are disjoint",
        disjoint,
        {name: len(rows) for name, rows in partitions.items()},
    )
    pipeline = get("http://localhost:8080/v1/pipeline/status")
    check(
        "Complete pipeline",
        all(stage["status"] == "completed" for stage in pipeline["stages"]),
        {s["name"]: s["status"] for s in pipeline["stages"]},
    )
    result = {
        "executed_at": time.time(),
        "checks": checks,
        "passed": sum(c["passed"] for c in checks),
        "failed": sum(not c["passed"] for c in checks),
    }
    Path("reports/runtime/runtime-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    if result["failed"]:
        raise SystemExit("Runtime verification failed")


if __name__ == "__main__":
    main()
