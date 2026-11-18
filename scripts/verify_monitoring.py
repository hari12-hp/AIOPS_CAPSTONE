"""Verify provisioned operations and optionally the real firing/resolved route."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROMETHEUS = "http://localhost:19090"
INBOX = "http://localhost:19199"


def get(url, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    with urlopen(
        Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=10
    ) as response:
        return json.load(response)


def wait_for_delivery(status, since, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = get(INBOX + "/events")["events"]
        for event in events:
            stamp = datetime.fromisoformat(event["received_at"]).timestamp()
            if event["kind"] == "drill" and event["status"] == status and stamp >= since:
                return event
        time.sleep(3)
    raise RuntimeError(f"No real AlertDeliveryDrill {status} delivery within {timeout}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--drill", action="store_true", help="Verify a temporary real firing/resolved alert"
    )
    args = parser.parse_args()
    checks = []

    def check(name, condition, detail):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        if not condition:
            raise RuntimeError(name)

    result = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "drill": args.drill,
        "checks": checks,
    }
    try:
        targets = get(PROMETHEUS + "/api/v1/targets")["data"]["activeTargets"]
        health = {t["labels"]["job"] + "/" + t["labels"]["instance"]: t["health"] for t in targets}
        check(
            "All configured scrape targets are up",
            len(targets) == 15 and all(v == "up" for v in health.values()),
            health,
        )
        probes = get(
            PROMETHEUS + "/api/v1/query?" + urlencode({"query": 'probe_success{job="http-probes"}'})
        )["data"]["result"]
        check(
            "Eight HTTP endpoints are ready",
            len(probes) == 8 and all(float(p["value"][1]) == 1 for p in probes),
            {p["metric"]["service"]: p["value"][1] for p in probes},
        )
        rules = get(PROMETHEUS + "/api/v1/rules")["data"]["groups"]
        all_rules = [rule for group in rules for rule in group["rules"]]
        check(
            "Recording and alert rules evaluate without errors",
            len(all_rules) >= 20 and all(r["health"] == "ok" for r in all_rules),
            len(all_rules),
        )
        managers = get(PROMETHEUS + "/api/v1/alertmanagers")["data"]["activeAlertmanagers"]
        check("Prometheus routes to Alertmanager", bool(managers), managers)
        check(
            "Alertmanager is ready",
            get("http://localhost:19093/api/v2/status")["uptime"] != "",
            "HTTP 200",
        )
        for uid in ("local-math-assistant", "math-alert-center", "math-mlops"):
            dashboard = get(f"http://localhost:13000/api/dashboards/uid/{uid}")["dashboard"]
            check(
                f"Provisioned dashboard: {uid}", len(dashboard["panels"]) >= 10, dashboard["title"]
            )
            expressions = {
                target["expr"]
                for panel in dashboard["panels"]
                for target in panel.get("targets", [])
                if "expr" in target
            }
            for expression in expressions:
                response = get(PROMETHEUS + "/api/v1/query?" + urlencode({"query": expression}))
                if response.get("status") != "success":
                    raise RuntimeError(f"Dashboard query failed: {expression}")
            check(f"Dashboard queries evaluate: {uid}", True, len(expressions))
        check("Local alert inbox is healthy", get(INBOX + "/health")["status"] == "ok", "HTTP 200")
        # A heartbeat is a real end-to-end delivery, not merely a ready HTTP server.
        deadline = time.monotonic() + 90
        while True:
            events = get(INBOX + "/events")["events"]
            heartbeat = next(
                (
                    e
                    for e in events
                    if e["kind"] == "heartbeat"
                    and datetime.fromisoformat(e["received_at"]).timestamp() > time.time() - 180
                ),
                None,
            )
            if heartbeat or time.monotonic() >= deadline:
                break
            time.sleep(3)
        check("Recent real Watchdog notification delivered", bool(heartbeat), heartbeat)
        if args.drill:
            since = time.time()
            print(
                "Enabling temporary signal; waiting for real Prometheus/Alertmanager delivery…",
                flush=True,
            )
            try:
                get(INBOX + "/drill", {"enabled": True})
                firing = wait_for_delivery("firing", since)
                check("Controlled alert reached inbox as firing", True, firing)
            finally:
                get(INBOX + "/drill", {"enabled": False})
            print("Signal disabled; waiting for resolved delivery…", flush=True)
            resolved = wait_for_delivery("resolved", since)
            check("Controlled alert reached inbox as resolved", True, resolved)
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        result["passed"] = sum(c["passed"] for c in checks)
        result["failed"] = sum(not c["passed"] for c in checks) + int(
            "error" in result and all(c["passed"] for c in checks)
        )
        destination = Path("reports/runtime/monitoring-verification.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Verification result: {destination}", flush=True)


if __name__ == "__main__":
    main()
