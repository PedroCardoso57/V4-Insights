# LGPD — inventário, retenção e atendimento a titulares

> Proposta técnica: validar bases legais, prazos e responsável (encarregado/DPO) com a
> unidade antes da produção.

## Inventário de dados pessoais

| Dado | Titular | Onde | Finalidade | Retenção padrão |
|---|---|---|---|---|
| Nome, e-mail, perfil, vínculo Google (`sub`) | Colaborador | `usuarios` | Autenticação e autorização | Enquanto ativo; anonimização sob pedido ou desligamento |
| Hash Argon2id da senha (opcional) | Colaborador | `usuarios.senha_hash` | Login por e-mail e senha | Até remoção pelo admin ou anonimização; a senha em si nunca é guardada |
| IP e user-agent de sessão | Colaborador | `sessoes` | Segurança e revogação | `SESSIONS_RETENTION_DAYS` (30) após expirar/revogar |
| Trilha de ações e IP | Colaborador | `auditoria` | Segurança e prestação de contas | `AUDIT_RETENTION_DAYS` (730) |
| CPF opcional de cliente pessoa física | Cliente PF | `clientes.documento` | Identificação do cliente | Enquanto o cliente existir; pode ser apagado na edição |
| Métricas de campanhas | — (dados agregados de anúncios) | `metricas_diarias` | Dashboards e relatórios | Sem dado pessoal |
| Tokens de provedores | — | `credenciais_integracao` (cifrado) | Coleta | Até a revogação |
| PDFs de relatórios | — (dados agregados) | Volume privado | Histórico | `REPORTS_RETENTION_DAYS` (90) |

O expurgo de sessões, states OAuth e auditoria vencidos roda diariamente no worker
(`v4.manutencao`); PDFs vencidos são removidos de hora em hora (`v4.limpar_relatorios`).

## Atendimento a titulares (colaboradores)

| Pedido | Como atender |
|---|---|
| Acesso / portabilidade | `docker compose run --rm api python -m app.cli lgpd-exportar --email pessoa@empresa.com --out titular.json` — perfil, carteira, sessões e trilha de auditoria em JSON. |
| Correção | Admin edita nome/perfil na tela **Usuários**. |
| Eliminação / anonimização | `... python -m app.cli lgpd-anonimizar --email pessoa@empresa.com --confirmar` — desativa, troca nome/e-mail por valores anônimos, desvincula o Google, apaga o hash da senha, revoga sessões e remove IPs; a trilha de auditoria permanece sem identificação para preservar a integridade. |
| Revogar acesso imediatamente | `... python -m app.cli revogar-sessoes --email pessoa@empresa.com` e desativar o usuário. |

Todos esses comandos ficam registrados na auditoria. Registre o pedido, a data e a resposta no
canal oficial do encarregado.

## Medidas de segurança

TLS no proxy, cookies `Secure`/`HttpOnly`/`SameSite`, CSRF, RBAC por cliente em cada rota,
segredos fora do Git, credenciais cifradas em repouso com chave fora do banco e rotação,
rate limit, proteção SSRF, logs sanitizados, backups cifrados com cópia externa e teste de
restauração mensal.
