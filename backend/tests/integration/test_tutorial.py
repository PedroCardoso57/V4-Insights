from __future__ import annotations


def test_tutorial_aparece_ate_ser_visto_e_pode_ser_revisto(factory) -> None:
    u = factory.usuario("analista")
    c = factory.login(u)
    assert c.get("/auth/me").json()["tutorial_visto"] is False

    assert c.put("/auth/tutorial", json={"visto": True}).status_code == 204
    assert c.get("/auth/me").json()["tutorial_visto"] is True
    # Repetir não muda nada (pular e concluir na mesma sessão, por exemplo).
    assert c.put("/auth/tutorial", json={"visto": True}).status_code == 204

    assert c.put("/auth/tutorial", json={"visto": False}).status_code == 204
    assert c.get("/auth/me").json()["tutorial_visto"] is False


def test_tutorial_e_por_usuario(factory) -> None:
    a = factory.login(factory.usuario("admin"))
    b = factory.login(factory.usuario("visualizador"))
    assert a.put("/auth/tutorial", json={"visto": True}).status_code == 204
    assert b.get("/auth/me").json()["tutorial_visto"] is False


def test_tutorial_exige_sessao(anon) -> None:  # type: ignore[no-untyped-def]
    assert anon.put("/auth/tutorial", json={"visto": True}).status_code in (401, 403)
