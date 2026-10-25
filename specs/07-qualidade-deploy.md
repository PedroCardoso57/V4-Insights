# SPEC-07 — Qualidade, segurança e produção

## Testes
Pytest: regras de domínio, agregações, permissões e callbacks simulados. Integração com PostgreSQL real em container; mocks para APIs Meta/Google. Frontend: testes unitários de componentes e Playwright E2E de login simulado, carteira, dashboards e relatórios. CI bloqueia merge quando testes ou migrations falham.

## Segurança
TLS no proxy; cookies seguros e CSRF; rate limit no login e endpoints caros; RBAC e verificação por cliente em cada rota; secrets fora do Git; credenciais criptografadas em repouso; tokens com rotação/revogação; proteção SSRF em URLs externas; sanitização de logs; cabeçalhos de segurança; política de retenção e atendimento LGPD. Nunca usar `email` como autorização isolada após vincular Google `sub`.

## VPS
Linux com atualizações automáticas de segurança, firewall apenas 80/443 e SSH restrito, acesso por chave, usuário sem privilégios para processos, volumes persistentes, PostgreSQL/Redis em rede interna, proxy Nginx ou Caddy, domínio e certificado TLS, monitoração e alertas. Worker com limites de concorrência e recursos.

## Backups/recuperação
Backup PostgreSQL diário criptografado e cópia fora da VPS; retenção inicial proposta 7 diários + 4 semanais (validar). Teste de restauração mensal; documentar RPO/RTO após aprovação. Backup de arquivos PDF e configurações necessárias.

## Operação
Logs JSON com correlation_id, métricas de API/jobs, alertas para erro persistente de sincronização, falha de backup, armazenamento alto e readiness. Runbook para deploy, rollback, restaurar banco, revogar credenciais e incidentes.

## Critérios de aceite
Deploy em homologação e produção reproduzível; rollback demonstrado; banco inacessível externamente; backup restaurado em ambiente isolado; testes de acesso indevido e CSRF aprovados; nenhuma credencial em logs.
