from __future__ import annotations

import logging

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


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(SanitizingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # httpx registra URLs completas (com access_token em query string no Meta).
    logging.getLogger("httpx").setLevel(logging.WARNING)
