"""Bounded, persistent local Alertmanager inbox; no external message delivery."""

from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import html
import re
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from threading import Lock
import time

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

MAX_BODY = 128 * 1024
ASSETS = Path(__file__).resolve().parents[2] / "monitoring"


def normalize_notification(payload):
    if not isinstance(payload, dict) or payload.get("status") not in {"firing", "resolved"}:
        raise ValueError("Expected an Alertmanager notification with firing/resolved status")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not 1 <= len(alerts) <= 100:
        raise ValueError("Expected 1–100 alerts")
    normalized = []
    for alert in alerts:
        if not isinstance(alert, dict) or alert.get("status") not in {"firing", "resolved"}:
            raise ValueError("Each alert needs a valid status")
        labels, annotations = alert.get("labels", {}), alert.get("annotations", {})
        if not isinstance(labels, dict) or not isinstance(annotations, dict):
            raise ValueError("Labels and annotations must be objects")
        if not isinstance(labels.get("alertname"), str) or not labels["alertname"]:
            raise ValueError("Each alert needs an alertname")
        normalized.append(
            {
                "status": alert["status"],
                "labels": {
                    key: str(labels[key])[:1000]
                    for key in (
                        "alertname",
                        "severity",
                        "component",
                        "service",
                        "instance",
                        "stage",
                        "environment",
                    )
                    if key in labels
                },
                "annotations": {
                    key: str(annotations[key])[:4000]
                    for key in ("summary", "description", "runbook_url")
                    if key in annotations
                },
                "startsAt": str(alert.get("startsAt", ""))[:100],
                "endsAt": str(alert.get("endsAt", ""))[:100],
            }
        )
    names = {alert["labels"]["alertname"] for alert in normalized}
    kind = (
        "heartbeat"
        if names == {"Watchdog"}
        else "drill"
        if names == {"AlertDeliveryDrill"}
        else "incident"
    )
    return {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": payload["status"],
        "kind": kind,
        "alerts": normalized,
    }


class DurableJournal(RotatingFileHandler):
    def handleError(self, record):
        raise OSError("Unable to persist alert notification")


class Inbox:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "notifications.jsonl"
        self.lock = Lock()
        self.registry = CollectorRegistry()
        self.received = Counter(
            "math_alert_receiver_notifications_total",
            "Delivered notification groups",
            ["kind", "status"],
            registry=self.registry,
        )
        self.last = Gauge(
            "math_alert_receiver_last_notification_timestamp_seconds",
            "Last delivery timestamp",
            ["kind"],
            registry=self.registry,
        )
        for kind in ("heartbeat", "incident", "drill"):
            self.last.labels(kind).set(0)
            for status in ("firing", "resolved"):
                self.received.labels(kind, status)
        self.started = time.time()
        self.last_heartbeat = 0.0
        Gauge(
            "math_alert_receiver_heartbeat_age_seconds",
            "Time since heartbeat, or startup during grace",
            registry=self.registry,
        ).set_function(lambda: max(0, time.time() - (self.last_heartbeat or self.started)))
        self.drill_until = 0.0
        Gauge(
            "math_alert_delivery_drill",
            "Temporary delivery test signal, auto expires",
            registry=self.registry,
        ).set_function(lambda: int(time.monotonic() < self.drill_until))
        self.logger = logging.Logger("alert-events")
        handler = DurableJournal(self.path, maxBytes=2 * 1024 * 1024, backupCount=4)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def receive(self, payload):
        event = normalize_notification(payload)
        with self.lock:
            self.logger.warning(json.dumps(event, ensure_ascii=True))
            os.fsync(self.logger.handlers[0].stream.fileno())
            self.received.labels(event["kind"], event["status"]).inc()
            self.last.labels(event["kind"]).set(time.time())
            if event["kind"] == "heartbeat":
                self.last_heartbeat = time.time()
        return event

    def events(self):
        with self.lock, self.path.open() as stream:
            lines = deque(stream, maxlen=200)
        events = []
        for line in reversed(lines):
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events

    def close(self):
        for handler in self.logger.handlers:
            handler.close()


def handler_for(inbox):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def reply(self, status, data, content_type="application/json; charset=utf-8"):
            if not isinstance(data, bytes):
                data = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self.reply(200, {"status": "ok"})
            elif path == "/events":
                self.reply(200, {"events": inbox.events()})
            elif path == "/metrics":
                self.reply(200, generate_latest(inbox.registry), "text/plain; version=0.0.4")
            elif path == "/":
                self.reply(
                    200, (ASSETS / "alert-inbox.html").read_bytes(), "text/html; charset=utf-8"
                )
            elif path == "/runbook":
                parts = [
                    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Operations runbook</title><style>body{color-scheme:dark;background:#181818;color:#ddd;font:15px/1.7 system-ui;max-width:900px;margin:40px auto;padding:0 24px}pre{white-space:pre-wrap;font:inherit}h2{padding-top:20px}a{color:#b7c9ed}</style><a href="/">← Alert inbox</a>'
                ]
                for line in (ASSETS / "RUNBOOK.md").read_text().splitlines():
                    if line.startswith("## "):
                        title = line[3:]
                        anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                        parts.append(f'<h2 id="{anchor}">{html.escape(title)}</h2>')
                    elif line.startswith("# "):
                        parts.append(f"<h1>{html.escape(line[2:])}</h1>")
                    else:
                        parts.append(f"<pre>{html.escape(line)}</pre>")
                self.reply(200, "\n".join(parts).encode(), "text/html; charset=utf-8")
            else:
                self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if self.path not in {"/alerts", "/drill"}:
                self.close_connection = True
                self.reply(404, {"error": "Not found"})
                return
            self.connection.settimeout(10)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    raise ValueError("Body must be 1–131072 bytes")
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    raise ValueError("Content-Type must be application/json")
                payload = json.loads(self.rfile.read(size))
                if self.path == "/alerts":
                    event = inbox.receive(payload)
                    self.reply(200, {"accepted": True, "kind": event["kind"]})
                else:
                    if not isinstance(payload, dict) or type(payload.get("enabled")) is not bool:
                        raise ValueError("enabled must be a boolean")
                    inbox.drill_until = time.monotonic() + 180 if payload["enabled"] else 0
                    self.reply(200, {"enabled": payload["enabled"], "auto_expires_seconds": 180})
            except OSError:
                self.close_connection = True
                self.reply(503, {"error": "Notification storage is unavailable"})
            except (ValueError, TypeError) as exc:
                self.close_connection = True
                self.reply(400, {"error": str(exc)})

        def log_message(self, fmt, *args):
            logging.getLogger("alert-inbox").info(fmt, *args)

    return Handler


def main():
    logging.basicConfig(level=logging.INFO)
    inbox = Inbox(os.getenv("ALERT_EVENT_DIR", "reports/runtime/alert-events"))
    server = ThreadingHTTPServer(("0.0.0.0", 9199), handler_for(inbox))
    server.daemon_threads = True
    try:
        server.serve_forever()
    finally:
        server.server_close()
        inbox.close()


if __name__ == "__main__":
    main()
