from __future__ import annotations

import logging

from app.core.logging import JsonFormatter, SanitizingFilter
from app.core.sanitize import sanitize


def test_remove_tokens_de_mensagens() -> None:
    msg = (
        "erro access_token=EAAB1234567890abcdefghijk&x=1 Bearer ya29.a0AfH6SM refresh_token: "
        "'1//0gabc-def' code=4/0AX4XfWh_abcdefghijklmnopqrstu"
    )
    out = sanitize(msg)
    for segredo in ("EAAB123", "ya29.", "1//0g", "4/0AX4"):
        assert segredo not in out
    assert "code=190" in sanitize("Meta 400 code=190: invalid")  # códigos de erro preservados


def test_log_estruturado_e_sanitizado() -> None:
    rec = logging.LogRecord(
        "t", logging.WARNING, __file__, 1, "token %s", ("access_token=abcdefghijklmnop",), None
    )
    SanitizingFilter().filter(rec)
    linha = JsonFormatter().format(rec)
    assert '"level": "WARNING"' in linha and "abcdefghijklmnop" not in linha
