"""Storage privado de arquivos gerados (PDFs).

As referências gravadas no banco são opacas (`local:<uuid>.pdf`) e nunca expõem caminhos
da VPS. O diretório deve ser um volume não servido pelo proxy.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from app.core.config import get_settings

_REF = re.compile(r"^local:([0-9a-f]{32})\.pdf$")


class StorageError(Exception):
    pass


def _dir() -> Path:
    d = Path(get_settings().reports_storage_dir)
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    return d


def _path(ref: str) -> Path:
    m = _REF.match(ref)
    if not m:
        raise StorageError("referência inválida")
    return _dir() / f"{m.group(1)}.pdf"


def salvar_pdf(conteudo: bytes) -> str:
    nome = uuid.uuid4().hex
    destino = _dir() / f"{nome}.pdf"
    tmp = destino.with_suffix(".tmp")
    tmp.write_bytes(conteudo)
    os.chmod(tmp, 0o600)
    tmp.replace(destino)  # gravação atômica
    return f"local:{nome}.pdf"


def ler(ref: str) -> bytes:
    p = _path(ref)
    if not p.exists():
        raise StorageError("arquivo indisponível")
    return p.read_bytes()


def remover(ref: str | None) -> None:
    if not ref:
        return
    p = _path(ref)
    p.unlink(missing_ok=True)
