"""Senhas locais (login por e-mail e senha): hash Argon2id e política mínima.

Só o hash é persistido. A verificação gasta o mesmo tempo quando o usuário não existe ou
não tem senha (hash fictício), para não revelar quais e-mails estão cadastrados.
"""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

TAMANHO_MINIMO = 10
TAMANHO_MAXIMO = 128


class SenhaFraca(ValueError):
    """Senha recusada pela política (mensagem segura para exibir ao usuário)."""


@lru_cache
def _hasher() -> PasswordHasher:
    # Perfil RFC 9106 de baixa memória (Argon2id, 64 MiB, t=3, p=4).
    return PasswordHasher()


@lru_cache
def _hash_ficticio() -> str:
    return _hasher().hash("senha-ficticia-para-tempo-constante")


def validar_politica(senha: str, email: str | None = None) -> None:
    if len(senha) < TAMANHO_MINIMO:
        raise SenhaFraca(f"A senha precisa ter pelo menos {TAMANHO_MINIMO} caracteres.")
    if len(senha) > TAMANHO_MAXIMO:
        raise SenhaFraca(f"A senha pode ter no máximo {TAMANHO_MAXIMO} caracteres.")
    if not senha.strip():
        raise SenhaFraca("A senha não pode ser só espaços.")
    if email and senha.strip().lower() in {email.lower(), email.split("@")[0].lower()}:
        raise SenhaFraca("A senha não pode ser igual ao e-mail.")


def gerar_hash(senha: str) -> str:
    return _hasher().hash(senha)


def verificar(senha_hash: str | None, senha: str) -> bool:
    try:
        _hasher().verify(senha_hash or _hash_ficticio(), senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return senha_hash is not None


def precisa_rehash(senha_hash: str) -> bool:
    return _hasher().check_needs_rehash(senha_hash)
