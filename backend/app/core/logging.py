from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.core.context import current_request_id
from app.core.sanitize import sanitize


class SanitizingFilter(logging.Filter):
    """Garante que tokens não cheguem aos logs, mesmo por engano."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg = sanitize(msg, max_len=4000)
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """Log estruturado (uma linha JSON por evento) com request_id de correlação."""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": current_request_id(),
        }
        if record.exc_info:
            data["exc"] = sanitize(self.formatException(record.exc_info), max_len=8000)
        return json.dumps(data, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SanitizingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # httpx registra URLs completas (com access_token em query string no Meta).
    logging.getLogger("httpx").setLevel(logging.WARNING)
