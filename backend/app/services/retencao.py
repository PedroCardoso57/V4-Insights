"""Política de retenção (SPEC-07/LGPD): expurgo de dados operacionais vencidos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Auditoria, OAuthState, Sessao


def expurgar(db: Session) -> dict[str, int]:
    s = get_settings()
    agora = datetime.now(UTC)
    limite_sessao = agora - timedelta(days=s.sessions_retention_days)
    r_sessoes = db.execute(
        delete(Sessao).where(
            or_(Sessao.expira_em < limite_sessao, Sessao.revogado_em < limite_sessao)
        )
    )
    # States OAuth são de uso único e valem minutos; 1 dia de folga para diagnóstico.
    r_states = db.execute(
        delete(OAuthState).where(OAuthState.expira_em < agora - timedelta(days=1))
    )
    r_audit = db.execute(
        delete(Auditoria).where(
            Auditoria.data_hora < agora - timedelta(days=s.audit_retention_days)
        )
    )
    db.commit()
    return {
        "sessoes": linhas(r_sessoes),
        "oauth_states": linhas(r_states),
        "auditoria": linhas(r_audit),
    }


def linhas(resultado: object) -> int:
    """Linhas afetadas por um DELETE/UPDATE (CursorResult.rowcount)."""
    return int(getattr(resultado, "rowcount", 0) or 0)
