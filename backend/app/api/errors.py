"""Contrato comum de erro (SPEC-08) e identificador de correlação por requisição.

{"error": {"code": "FORBIDDEN", "message": "Acesso não autorizado", "request_id": "..."}}
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.context import current_request_id, request_id_var

__all__ = ["AppError", "ERROR_RESPONSES", "current_request_id", "install"]

log = logging.getLogger(__name__)

_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "PROVIDER_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(HTTPException):
    """HTTPException com código de erro explícito (ex.: PROVIDER_QUOTA)."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code, message, headers=headers)
        self.code = code or CODES.get(status_code, "ERROR")


def _body(
    status_code: int,
    message: str,
    code: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    err = ErrorBody(
        code=code or CODES.get(status_code, "ERROR"),
        message=message,
        request_id=current_request_id(),
        details=details,
    )
    return JSONResponse({"error": err.model_dump(exclude_none=True)}, status_code=status_code)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        recebido = request.headers.get("x-request-id", "")
        rid = recebido if _VALID_ID.match(recebido) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


def install(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else CODES.get(exc.status_code, "")
        resp = _body(exc.status_code, message, getattr(exc, "code", None))
        if exc.headers:
            resp.headers.update(exc.headers)
        return resp

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": [str(p) for p in e.get("loc", ())], "msg": e.get("msg", "")}
            for e in exc.errors()
        ]
        return _body(422, "Dados inválidos", details=details)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("erro não tratado: %s", exc.__class__.__name__)
        return _body(500, "Erro interno. Informe o request_id ao suporte.")


# Respostas de erro documentadas no OpenAPI de todas as rotas de negócio.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse, "description": CODES[code]}
    for code in (401, 403, 404, 409, 422, 429)
}
