from __future__ import annotations

import io

from PIL import Image
from sqlalchemy import select

from app.models import Auditoria, UsuarioFoto
from app.services import lgpd


def _imagem(fmt: str = "JPEG", tamanho: tuple[int, int] = (640, 480)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", tamanho, (229, 9, 20))
    exif = Image.Exif()
    exif[0x010F] = "Camera Secreta"  # Make
    img.save(buf, fmt, exif=exif) if fmt == "JPEG" else img.save(buf, fmt)
    return buf.getvalue()


def _enviar(c, uid, conteudo: bytes, tipo: str = "image/jpeg"):  # type: ignore[no-untyped-def]
    return c.put(f"/usuarios/{uid}/foto", content=conteudo, headers={"Content-Type": tipo})


def test_usuario_envia_a_propria_foto_e_admin_ve(factory, db) -> None:
    u = factory.usuario("analista")
    c = factory.login(u)
    assert c.get("/auth/me").json()["foto_url"] is None

    r = _enviar(c, u.id, _imagem())
    assert r.status_code == 200, r.text
    url = r.json()["foto_url"]
    assert url.startswith(f"/api/v1/usuarios/{u.id}/foto?v=")
    assert c.get("/auth/me").json()["foto_url"] == url

    admin = factory.login(factory.usuario("admin"))
    lista = admin.get("/usuarios").json()["items"]
    assert next(x for x in lista if x["id"] == str(u.id))["foto_url"] == url

    img = admin.get(url)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/webp"
    assert "max-age" in img.headers["cache-control"]
    salva = Image.open(io.BytesIO(img.content))
    assert salva.format == "WEBP" and salva.size == (256, 256)
    assert not salva.getexif()  # metadados descartados

    acoes = db.scalars(select(Auditoria.acao).where(Auditoria.entidade_id == u.id)).all()
    assert "definir_foto" in acoes


def test_troca_e_remocao(factory, db) -> None:
    u = factory.usuario()
    c = factory.login(u)
    assert _enviar(c, u.id, _imagem("PNG", (300, 900)), "image/png").status_code == 200
    assert _enviar(c, u.id, _imagem("WEBP"), "image/webp").status_code == 200
    assert len(db.scalars(select(UsuarioFoto)).all()) == 1

    assert c.delete(f"/usuarios/{u.id}/foto").status_code == 204
    assert c.get("/auth/me").json()["foto_url"] is None
    assert c.get(f"/usuarios/{u.id}/foto").status_code == 404
    assert c.delete(f"/usuarios/{u.id}/foto").status_code == 204  # idempotente


def test_somente_dono_ou_admin_altera(factory) -> None:
    alvo = factory.usuario()
    gestor = factory.login(factory.usuario("gestor"))
    assert _enviar(gestor, alvo.id, _imagem()).status_code == 403
    assert gestor.delete(f"/usuarios/{alvo.id}/foto").status_code == 403

    admin = factory.login(factory.usuario("admin"))
    assert _enviar(admin, alvo.id, _imagem()).status_code == 200
    assert admin.delete(f"/usuarios/{alvo.id}/foto").status_code == 204


def test_recusa_arquivo_que_nao_e_imagem(factory) -> None:
    u = factory.usuario()
    c = factory.login(u)
    r = _enviar(c, u.id, b"<svg onload=alert(1)>", "image/png")
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"
    assert _enviar(c, u.id, b"").status_code == 422
    grande = _enviar(c, u.id, b"0" * (8 * 1024 * 1024 + 1))
    assert grande.status_code == 413


def test_foto_exige_login(anon, factory) -> None:
    u = factory.usuario()
    assert anon.get(f"/usuarios/{u.id}/foto").status_code == 401


def test_lgpd_anonimizar_remove_foto(factory, db) -> None:
    u = factory.usuario()
    c = factory.login(u)
    _enviar(c, u.id, _imagem())
    lgpd.anonimizar(db, u.email)
    assert db.get(UsuarioFoto, u.id) is None
