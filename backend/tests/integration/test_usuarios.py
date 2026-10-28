"""CRUD de usuários pela tela de administração, com foco na exclusão."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Auditoria, Usuario, UsuarioCliente


def test_excluir_anonimiza_revoga_e_some_da_listagem(factory, db) -> None:
    admin_u = factory.usuario("admin")
    admin = factory.login(admin_u)
    alvo_u = factory.usuario("analista", email="Bia@V4.com", sub="google-123")
    alvo = factory.login(alvo_u)
    factory.cliente(membros=(alvo_u,))
    assert alvo.get("/auth/me").status_code == 200

    assert admin.delete(f"/usuarios/{alvo_u.id}").status_code == 204

    assert alvo.get("/auth/me").status_code == 401
    emails = [u["email"] for u in admin.get("/usuarios").json()["items"]]
    assert "bia@v4.com" not in [e.lower() for e in emails]
    assert admin.get(f"/usuarios/{alvo_u.id}").status_code == 404
    assert admin.patch(f"/usuarios/{alvo_u.id}", json={"nome": "Volta"}).status_code == 404
    assert admin.delete(f"/usuarios/{alvo_u.id}").status_code == 404

    db.expire_all()
    u = db.get(Usuario, alvo_u.id)
    assert u is not None and u.excluido_em is not None and not u.ativo
    assert "bia" not in u.email.lower() and u.google_sub is None and u.senha_hash is None
    assert db.scalar(select(UsuarioCliente).where(UsuarioCliente.usuario_id == u.id)) is None
    evento = db.scalar(
        select(Auditoria).where(Auditoria.acao == "excluir", Auditoria.entidade_id == u.id)
    )
    assert evento is not None and evento.usuario_id == admin_u.id


def test_email_de_excluido_pode_ser_recadastrado(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    alvo = factory.usuario("analista", email="bia@v4.com")
    assert admin.delete(f"/usuarios/{alvo.id}").status_code == 204
    r = admin.post("/usuarios", json={"nome": "Bia", "email": "bia@v4.com", "papel": "analista"})
    assert r.status_code == 201


def test_admin_nao_exclui_a_si_mesmo(factory) -> None:
    admin_u = factory.usuario("admin")
    factory.usuario("admin")  # há outro admin: a recusa é só por ser o próprio usuário
    admin = factory.login(admin_u)
    r = admin.delete(f"/usuarios/{admin_u.id}")
    assert r.status_code == 400
    assert admin.get("/auth/me").status_code == 200


def test_ultimo_admin_ativo_e_protegido(factory, db) -> None:
    # Pela API o chamador é sempre um admin ativo, então a regra é exercida direto na função.
    from fastapi import HTTPException

    from app.api.v1.routes.usuarios import _garantir_outro_admin

    ultimo = factory.usuario("admin")
    factory.usuario("admin", ativo=False)  # admin inativo não conta
    with pytest.raises(HTTPException) as exc:
        _garantir_outro_admin(db, ultimo)
    assert exc.value.status_code == 409
    factory.usuario("admin")
    _garantir_outro_admin(db, ultimo)  # com outro admin ativo, passa


def test_rebaixar_ou_desativar_admin_exige_outro_admin(factory) -> None:
    a1 = factory.usuario("admin")
    a2 = factory.usuario("admin")
    c1 = factory.login(a1)
    assert c1.patch(f"/usuarios/{a2.id}", json={"papel": "gestor"}).status_code == 200
    assert c1.patch(f"/usuarios/{a2.id}", json={"papel": "admin"}).status_code == 200
    assert c1.patch(f"/usuarios/{a2.id}", json={"ativo": False}).status_code == 200


@pytest.mark.parametrize("papel", ["analista", "visualizador", "gestor"])
def test_somente_admin_exclui(factory, papel) -> None:
    c = factory.login(factory.usuario(papel))
    alvo = factory.usuario("visualizador")
    assert c.delete(f"/usuarios/{alvo.id}").status_code == 403


def test_editar_nome_e_papel(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    alvo = factory.usuario("analista")
    r = admin.patch(f"/usuarios/{alvo.id}", json={"nome": " Novo Nome ", "papel": "gestor"})
    assert r.status_code == 200
    assert r.json()["nome"] == "Novo Nome" and r.json()["papel"] == "gestor"
