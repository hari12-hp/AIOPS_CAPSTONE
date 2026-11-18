# Monitoring and Incident Operations

The local stack now has nine services: frontend, backend, MLflow model serving, MLflow tracking, Prometheus, Grafana, Alertmanager, Blackbox Exporter and a persistent alert receiver. Seven exporter targets and eight HTTP endpoint probes are collected every fifteen seconds. Six recording rules and seventeen alert rules are provisioned as source files.

## Operator views

| View | Purpose |
|---|---|
| Grafana Service Operations | Metrics/HTTP readiness, incident count, solve throughput, 5xx ratio, p50/p95/p99 latency, process RSS/CPU, in-flight requests and scrape timing |
| Grafana Alert Center | Severity queue, pending/firing state, notification delivery/failures, heartbeat age, silences and operating policy |
| Grafana ML Pipeline | Last measured stage durations and outcomes, running-stage elapsed time, Spark throughput, five-case acceptance score and model state |
| Alertmanager | Current grouped alerts, inhibition status and bounded maintenance silences |
| Local alert inbox | Delivered firing/resolved event history, heartbeat and controlled-drill history |

The service dashboard is http://localhost:13000/d/local-math-assistant. Alert Center is http://localhost:13000/d/math-alert-center; ML lifecycle is http://localhost:13000/d/math-mlops. Alertmanager runs at http://localhost:19093/ and the inbox at http://localhost:19199/.

## Alert policy and scope

Availability alerts hold for one minute. Traffic alerts exclude HTTP 4xx from the server-error numerator. Warning errors exceed 5% with at least five requests in ten minutes; critical errors exceed 20% with at least ten requests. Both hold for two minutes. End-to-end solve p95 latency above thirty seconds requires ten requests in ten minutes and a five-minute hold. Additional rules cover in-flight queue pressure, model RSS, pipeline parent/stage failures, stalled training, generation-gate failure, configuration reload failure and notification-delivery failure.

Latency buckets extend to 180 seconds for CPU inference. In-flight counts include waiting requests because inference is serialized. RSS and CPU are process metrics; 100% CPU means one core. Observed HTTP uptime describes collected samples, not a guaranteed full-day production SLO. No traffic produces no latency estimate. The five-case smoke score remains distinct from broad mathematical correctness.

Prometheus evaluates alerts, and Alertmanager groups, deduplicates, inhibits and routes them. Critical incidents suppress warnings for the same component; scrape outages suppress duplicate endpoint alerts. The local receiver accepts bounded validated notifications, flushes them to a rotating journal, and responds with a retryable error when durable storage is unavailable. The UI renders event text safely. External email/chat notification destinations are not configured.

<!-- pagebreak -->

## Verification and operations

The Watchdog alert is intentionally always firing and delivers a heartbeat roughly every minute. It is excluded from incident counts. A missing-heartbeat rule has startup grace. A temporary delivery drill goes through the real metric, rule, routing and webhook path and must deliver both firing and resolved notifications.

```bash
.venv/bin/python scripts/verify_monitoring.py --drill
```

The verifier checks all dashboard PromQL expressions, healthy target inventory, readiness probes, rule health, routing, the persistent inbox and recent Watchdog delivery. Promtool tests cover hold/recovery behavior, low-volume gating, thresholds, lifecycle and 4xx exclusion. Python tests cover durable concurrent storage, bounded input/history, failure retry, drill expiry and the new API/pipeline telemetry. The refreshed suite has 58 passing cases.

Named Docker volumes retain monitoring state across recreation. Prometheus retention is bounded to fifteen days or two GB; inbox files rotate at two MiB with four backups. The UI shows the latest 200 deliveries from the current journal. A timed silence should identify an owner and the smallest affected service. The complete recovery and maintenance guide is `monitoring/RUNBOOK.md`, also served from http://localhost:19199/runbook.

This is a local operations setup. An entire host outage requires monitoring and delivery outside that host. Production exposure would additionally require access control, capacity policy, secret management, backups and deployment-specific threshold calibration.
