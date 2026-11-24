"""JSON-line logging to stdout (configured once at startup)."""

import json
import logging
import sys
from datetime import datetime, timezone


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload = dict(structured)
            payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
            payload.setdefault("level", record.levelname)
            payload.setdefault("logger", record.name)
        else:
            payload = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        if record.exc_info and record.levelno >= logging.ERROR:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLineFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def log_chat_audit(payload: dict) -> None:
    logging.getLogger("app.audit").info("chat", extra={"structured": payload})