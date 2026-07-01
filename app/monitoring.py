import os
import json
import time
import logging
import threading
from datetime import datetime, timezone

def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()
from collections import defaultdict, deque

_request_log_lock = threading.Lock()
_request_log = defaultdict(lambda: deque(maxlen=1000))

_error_log_lock = threading.Lock()
_error_log = deque(maxlen=500)


class MetricsCollector:
    """Thread-safe metrics collector for application observability."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._gauges = {}
        self._timings = defaultdict(list)
        self._alerts = deque(maxlen=200)

    def increment(self, metric: str, value: int = 1) -> None:
        with self._lock:
            self._counters[metric] += value

    def gauge(self, metric: str, value: float) -> None:
        with self._lock:
            self._gauges[metric] = value

    def timing(self, metric: str, duration_ms: float) -> None:
        with self._lock:
            self._timings[metric].append(duration_ms)
            if len(self._timings[metric]) > 1000:
                self._timings[metric] = self._timings[metric][-1000:]

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        self.increment(f"requests.{method}.{status_code}")
        self.increment("requests.total")
        self.timing(f"request.{method}.{path}", duration_ms)

        with _request_log_lock:
            _request_log[path].append({
                "timestamp": datetime.utcnow().isoformat(),
                "method": method,
                "status": status_code,
                "duration_ms": duration_ms,
            })

    def record_error(self, error_type: str, message: str, context: dict = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,
            "message": message,
            "context": context or {},
        }
        with _error_log_lock:
            _error_log.append(entry)

    def alert(self, severity: str, message: str, context: dict = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "message": message,
            "context": context or {},
        }
        with self._lock:
            self._alerts.append(entry)

        if severity in ("critical", "fatal"):
            self._send_alert_notification(entry)

    def _send_alert_notification(self, entry: dict) -> None:
        try:
            from app import mail, create_app
            app = create_app()
            with app.app_context():
                admin_recipients = [
                    u.email for u in __import__("app.models", fromlist=["User"]).User.query.filter_by(role="admin").all()
                    if u.email
                ]
                if admin_recipients:
                    from flask_mail import Message
                    msg = Message(
                        subject=f"[SarkinMota ALERT] {entry['severity'].upper()}: {entry['message'][:100]}",
                        recipients=admin_recipients,
                        body=json.dumps(entry, indent=2),
                    )
                    mail.send(msg)
        except Exception:
            pass

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": {
                    k: {
                        "count": len(v),
                        "avg_ms": sum(v) / len(v) if v else 0,
                        "p95_ms": sorted(v)[int(len(v) * 0.95)] if v else 0,
                        "max_ms": max(v) if v else 0,
                    }
                    for k, v in self._timings.items()
                },
                "alerts": list(self._alerts),
            }

    def get_recent_errors(self, limit: int = 100) -> list:
        with _error_log_lock:
            return list(_error_log)[-limit:]

    def get_request_log(self, path: str = None, limit: int = 100) -> list:
        with _request_log_lock:
            if path:
                return list(_request_log.get(path, []))[-limit:]
            all_entries = []
            for entries in _request_log.values():
                all_entries.extend(entries)
            all_entries.sort(key=lambda x: x["timestamp"], reverse=True)
            return all_entries[:limit]


metrics = MetricsCollector()


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": _utcnow_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        return json.dumps(log_entry)


class RequestLoggingMiddleware:
    """WSGI middleware for structured request logging and metrics."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("sarkinmota.requests")

    def __call__(self, environ, start_response):
        start_time = time.perf_counter()
        request_id = environ.get("HTTP_X_REQUEST_ID", f"req_{int(time.time() * 1000)}")
        environ["REQUEST_ID"] = request_id

        status_info = {}
        def custom_start_response(status, headers):
            status_info["status"] = status
            return start_response(status, headers)

        try:
            response = self.app(environ, custom_start_response)
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = int(status_info.get("status", "500").split()[0])
            method = environ.get("REQUEST_METHOD", "UNKNOWN")
            path = environ.get("PATH_INFO", "/")

            metrics.record_request(method, path, status_code, duration_ms)

            extra = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": status_code,
                "duration_ms": round(duration_ms, 2),
                "remote_addr": environ.get("REMOTE_ADDR"),
                "user_agent": environ.get("HTTP_USER_AGENT", ""),
            }
            self.logger.info(
                f"{method} {path} {status_code} {duration_ms:.1f}ms",
                extra={"extra_data": extra, "request_id": request_id}
            )

            if status_code >= 500:
                metrics.alert(
                    severity="critical" if status_code >= 500 else "warning",
                    message=f"HTTP {status_code} on {method} {path}",
                    context={"request_id": request_id, "path": path},
                )

            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            method = environ.get("REQUEST_METHOD", "UNKNOWN")
            path = environ.get("PATH_INFO", "/")
            metrics.record_error(type(e).__name__, str(e), {"path": path, "request_id": request_id})
            metrics.alert("critical", f"Unhandled exception: {str(e)}", {"path": path})
            raise


def setup_production_logging(app) -> None:
    """Configure production-grade logging with structured output."""
    if app.debug or app.testing:
        return

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = StructuredFormatter()

    app_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "sarkinmota.log"),
        maxBytes=50 * 1024 * 1024,
        backupCount=20,
    )
    app_log_handler.setFormatter(formatter)
    app_log_handler.setLevel(logging.INFO)

    error_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=50 * 1024 * 1024,
        backupCount=10,
    )
    error_log_handler.setFormatter(formatter)
    error_log_handler.setLevel(logging.ERROR)

    request_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "requests.log"),
        maxBytes=100 * 1024 * 1024,
        backupCount=10,
    )
    request_log_handler.setFormatter(formatter)
    request_log_handler.setLevel(logging.INFO)

    for logger_name in ("sarkinmota", "sarkinmota.requests", "sarkinmota.errors"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(logging.INFO)
        logger.addHandler(app_log_handler)
        logger.addHandler(error_log_handler if "errors" in logger_name else request_log_handler)
        logger.propagate = False

    app.logger.handlers.clear()
    app.logger.addHandler(app_log_handler)
    app.logger.addHandler(error_log_handler)
    app.logger.setLevel(logging.INFO)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(request_log_handler)
    werkzeug_logger.setLevel(logging.WARNING)

    app.logger.info("Structured logging configured")
