# SPEC-09 — Roadmap, sprints e entregas

Estimativas abaixo são planejamento inicial, não prazos garantidos. A implementação depende da aprovação de credenciais Meta/Google e validação dos requisitos funcionais.

## Sprint 1 — Fundação (P0)
- V4-001 Monorepo, lint e documentação (2h)
- V4-002 Docker/PostgreSQL/Redis e health checks (4h)
- V4-003 Alembic baseline, migration e rollback (5h)
- V4-004 Configurar Google OIDC (4h)
- V4-005 Pré-cadastro e RBAC (6h)
- V4-006 Sessões e CSRF (6h)
- V4-007 CRUD de clientes e isolamento (8h)
- V4-008 Administração de usuários (7h)
- V4-009 Testes e CI (7h)
- V4-010 VPS/homologação (6h)
- V4-011 Documento de permissões Meta/Google (4h)

**Total preliminar:** 59 horas. **Aceite:** login interno, gestão de clientes, banco versionado e ambiente homologado.

## Sprint 2 — Integrações (P0)
- Autorização Meta e Google Ads, descoberta de contas, storage de credenciais.
- Workers de coleta, normalização, idempotência, histórico de jobs e retry.
- Fixtures e testes de provedores, logs sanitizados, status de sincronização.
- **Aceite:** ao menos uma conta real autorizada de cada plataforma sincroniza dados; casos de erro simulados são tratados.

## Sprint 3 — Dashboards (P0)
- Endpoints agregados, filtros por período/cliente/plataforma, KPIs e gráficos.
- Painel geral, lista de campanhas, comparação de períodos e avisos de freshness.
- **Aceite:** números conferidos com amostras dos provedores e filtros consistentes.

## Sprint 4 — Relatórios (P0)
- Templates, editor, preview, worker de PDF, histórico e download privado.
- **Aceite:** PDF reproduz dados selecionados e não pode ser acessado fora da carteira.

## Sprint 5 — Hardening e go-live (P0)
- Testes E2E, auditoria, performance, acessibilidade, backup/restauração, monitoramento, segurança, documentação operacional e deploy.
- **Aceite:** checklist de produção aprovado, runbook, rollback e teste de restauração executados.

## Ordem de dependências
`SPEC-00 → SPEC-01 → SPEC-02 → SPEC-03 → SPEC-04 → SPEC-05 → SPEC-07`. `SPEC-06` acompanha os módulos funcionais; `SPEC-08` acompanha todos os ciclos.

## Distribuição sugerida
Backend A: autenticação, clientes, dados e API. Backend B: conectores, jobs e relatórios. Frontend: UX, dashboards e editor. QA/DevOps: testes, CI/CD, segurança e VPS. Um responsável técnico valida contratos e migrations antes de merges.

## Instruções para agente de implementação
1. Ler `specs/README.md` e a SPEC correspondente; verificar código existente antes de alterar.
2. Implementar somente o escopo da tarefa, sem inventar endpoints ou alterar migrations aplicadas.
3. Adicionar testes de sucesso, erro, autorização e isolamento por cliente.
4. Atualizar OpenAPI, documentação e exemplos de ambiente.
5. Entregar resumo de arquivos alterados, comandos de teste, riscos e pendências; não afirmar testes executados sem executá-los.
