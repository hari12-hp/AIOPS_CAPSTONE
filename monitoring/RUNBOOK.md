# Math Studio operations runbook

## Availability

Critical alerts: MathTargetUnavailable and MathEndpointUnavailable.

Start with http://localhost:19090/targets and http://localhost:19090/rules.
Check which component failed; exporter UP and HTTP readiness are separate.

    docker compose ps
    docker compose logs --tail=100 backend model-serving frontend
    docker compose logs --tail=100 blackbox prometheus

For an unconfigured or unloaded model, verify the champion alias and pinned cache.
Use scripts/restore_registry.sh only when registration is missing. After confirming
configuration and artifacts, restart the affected service and verify HTTP readiness:

    docker compose restart model-serving
    .venv/bin/python scripts/verify_runtime.py

HTTP checks cover eight endpoints. A probe inventory alert means configuration or
scraping is missing, not necessarily that the application returned an error.

## Errors and latency

MathSolveErrorsHigh: HTTP 5xx ratio >5% for 2m, at least 5 requests in 10m.
MathSolveErrorsCritical: ratio >20% for 2m, at least 10 requests in 10m.
MathSolveLatencyHigh: p95 >30s for 5m, at least 10 requests in 10m.

These are initial local CPU operating thresholds, not production SLO guarantees.
HTTP 4xx validation failures are excluded from the server-error ratio. Do not hide
an incident by changing thresholds before understanding its cause.

    docker compose logs --tail=100 backend model-serving

Compare request rate, in-flight requests, RSS and CPU with latency. The API
histogram extends to 180s and includes queue time; no traffic has no latency
estimate. Ask shorter questions to diagnose long-answer generation. Failed model
requests should produce 503, rather than fabricated mathematical answers.

## Capacity

MathSolveQueuePressure: more than 4 in-flight solve requests for 5m.
MathModelMemoryHigh: model process RSS >5.5 GiB for 5m.

Inference is serialized; in-flight requests include queued requests. RSS is process
resident memory, not host/container utilization. CPU 100% means one core; a
multithreaded model may exceed 100%. No Docker socket or privileged host exporter
is mounted. Use docker stats locally to investigate container or host pressure.

Stop unnecessary concurrent workloads and investigate oversized prompts. Revisit
capacity and thresholds after measuring the target machine. A real production
rollout additionally needs authentication, capacity limits, backups and a separate
monitoring failure domain; this repository remains a loopback-only local stack.

## Pipeline and model quality

MathPipelineFailed identifies a failed stage; MathPipelineRunFailed also catches
parent-run interruption. MathTrainingStalled means the train stage has run for
more than two hours, sustained 5m. The demo epoch usually takes 25–30 minutes;
slower hardware may legitimately require a different threshold.

    tail -n 100 reports/runtime/pipeline.log

Inspect http://localhost:8081/ and the matching MLflow run before retrying. Preserve
failure evidence. A cached run reuses previous stage metrics. Do not present it as
new training. MathGenerationGateFailed means the declared five-case smoke score
fell below 80%; it is a release gate, not broad mathematical accuracy. Do not
promote a candidate whose hash or acceptance evidence is invalid.

## Monitoring integrity

MathPrometheusConfigReloadFailed: rejected configuration for 1m.
MathAlertDeliveryFailing: a failed delivery in the last 10m, sustained 1m.
MathAlertHeartbeatMissing: no heartbeat for 3m, sustained another 1m.
Watchdog is intentionally always firing with severity info and is not an incident.
It routes to the local inbox roughly every minute. The first three minutes provide
startup grace. A dead entire Docker host cannot notify through this same host;
independent external monitoring is required to cover that failure mode.

    docker compose logs --tail=100 prometheus alertmanager alert-receiver
    docker compose exec -T prometheus promtool check config /etc/prometheus/prometheus.yml
    docker compose exec -T alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

Prometheus owns the alert rules. Grafana exposes their state and the external
Alertmanager data source; it does not duplicate evaluation. Alertmanager groups
and deduplicates alerts. Critical alerts suppress warnings for the same component;
metrics-target failures suppress duplicate endpoint-failure alerts. Delivery groups
are not unique incident counts.

## Delivery drill

    .venv/bin/python scripts/verify_monitoring.py --drill

The verifier enables a local metric for at most 180s. Prometheus evaluates it and
fires AlertDeliveryDrill after 15s; Alertmanager routes it to the inbox. The script
checks the real firing notification, disables the signal in a finally block, and
checks the resolved notification. Nothing is injected directly into the journal.
No application service is stopped and no email or chat messages are sent. The
result is saved to reports/runtime/monitoring-verification.json.

The information-level drill is separate from incident counts. Its delivery history
remains clearly labelled. Real availability and error rules have their own hold
periods and are covered by promtool unit tests in monitoring/tests/alerts.test.yml.

## Silences and maintenance

Use http://localhost:19093/ to create a bounded silence with an owner/comment and
an expiry. Match the smallest affected service/component. Review silenced alerts,
confirm recovery, then remove the silence. Do not disable evaluation globally.
Warning reminders repeat every 4h; critical reminders every 1h. Resolved events
are delivered to the local inbox. There is deliberately no unconfigured email
receiver or placeholder external webhook.

## Retention and recovery

Named Docker volumes preserve Grafana, Prometheus, Alertmanager silences and the
local notification journal across container recreation. Prometheus keeps at most
15 days or 2 GB (whichever is reached first). Inbox files rotate at 2 MiB with four
backups; the UI shows the latest 200 deliveries in the current file. Backups are
for inspection on the volume; the UI is not a permanent incident database.

    docker compose stop
    docker compose up -d --wait --wait-timeout 300

These preserve volumes. Do not use docker compose down -v unless deliberately
resetting all monitoring history and silences. Dashboard/rule sources live in
monitoring/ and are versionable. Never put notification credentials in Git. An
external email/Slack/PagerDuty receiver can be added later with the owner's
chosen destination and secret configuration.

## Configuration references

Prometheus alert rules: https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
Alertmanager routing: https://prometheus.io/docs/alerting/latest/configuration/
Grafana Alertmanager data source: https://grafana.com/docs/grafana/latest/datasources/alertmanager/
Blackbox probe configuration: https://github.com/prometheus/blackbox_exporter/blob/master/CONFIGURATION.md
