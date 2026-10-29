"""Normalização das fotos de perfil enviadas pelos colaboradores.

Toda imagem é decodificada e regravada: corta no centro, reduz para 256x256 e salva em WEBP
sem EXIF (localização, modelo da câmera). Arquivos que não são imagem são recusados.
"""

from __future__ import annotations

import io
from datetime import datetime

from PIL import Image, ImageOps, UnidentifiedImageError

LADO = 256
TAMANHO_MAXIMO = 8 * 1024 * 1024  # bytes aceitos no envio, antes da normalização
_FORMATOS = {"JPEG", "PNG", "WEBP", "GIF"}
_MAX_PIXELS = 40_000_000  # ~ 8000x5000; acima disso o Pillow recusa (bomba de descompressão)


class FotoInvalida(ValueError):
    pass


def normalizar(conteudo: bytes) -> bytes:
    if not conteudo:
        raise FotoInvalida("Envie um arquivo de imagem.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise FotoInvalida("A imagem deve ter no máximo 8 MB.")
    Image.MAX_IMAGE_PIXELS = _MAX_PIXELS
    try:
        with Image.open(io.BytesIO(conteudo)) as original:
            if original.format not in _FORMATOS:
                raise FotoInvalida("Use uma imagem JPG, PNG ou WEBP.")
            original.load()
            img = ImageOps.exif_transpose(original)  # respeita a orientação da câmera
            img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
            img = ImageOps.fit(img, (LADO, LADO), Image.Resampling.LANCZOS)
            saida = io.BytesIO()
            img.save(saida, "WEBP", quality=85, method=4)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise FotoInvalida("Não foi possível ler a imagem. Use JPG, PNG ou WEBP.") from exc
    return saida.getvalue()


def url_foto(usuario_id: object, atualizada_em: datetime | None) -> str | None:
    """URL relativa da foto; o parâmetro `v` muda a cada troca para furar o cache."""
    if atualizada_em is None:
        return None
    return f"/api/v1/usuarios/{usuario_id}/foto?v={int(atualizada_em.timestamp())}"
