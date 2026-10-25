# SPEC-08 — Dados, migrations e contratos

## Baseline existente
A migration inicial `backend/migrations/001_initial.sql` contém `perfis`, `usuarios`, `clientes`, `usuarios_clientes`, `integracoes`, `contas_anuncio`, `metricas_diarias`, `dashboards`, `dashboard_widgets`, `relatorios`, `relatorio_execucoes`, `auditoria`. Preservar dados existentes e migrar para Alembic sem aplicar novamente em bases já inicializadas.

## Ajustes necessários em migration incremental 002
- Criar `sync_jobs`: id UUID PK, integracao_id FK, status, periodo_inicio/fim, tentativa, idempotency_key UNIQUE por integração, total_registros, erro_sanitizado, iniciado_em, finalizado_em, criado_em.
- Criar `sessoes`: id UUID PK, usuario_id FK, token_hash UNIQUE, expira_em, revogado_em, criado_em, ultimo_acesso_em; nunca armazenar token de sessão em texto puro.
- Adicionar `atualizado_em` em dashboards e relatórios; definir índices para filtros mais usados.
- Adicionar `metricas_diarias` campos opcionais de identificação de campanha/conjunto/anúncio ou criar dimensões próprias conforme resposta dos provedores; nunca assumir que ID externo é global entre plataformas.
- Criar `credenciais_integracao` somente se necessário para guardar metadados criptografados, sem duplicar segredos em `integracoes`.
- Documentar exclusões e integridade referencial, constraints e unicidade por provedor/conta.

## Contratos comuns
- Sucesso lista: `{ "items": [], "page": 1, "page_size": 20, "total": 0 }`.
- Erro: `{ "error": { "code": "FORBIDDEN", "message": "Acesso não autorizado", "request_id": "..." } }`.
- Validação: HTTP 422; não autenticado: 401; sem permissão: 403; recurso de outro cliente: 404; conflito: 409; limite: 429; erro de provedor: 502/503 conforme causa.
- `POST` de tarefas assíncronas responde 202 com `job_id` e endpoint de consulta.
- Paginação limitada a 100 itens por página; timestamps ISO 8601 com offset; dinheiro como string decimal no JSON.
- Documentar filtros e enumerações no OpenAPI; gerar cliente TypeScript a partir do schema, evitando divergências.

## Critérios de aceite
Migrations executam em base limpa e base já inicializada; schema tem FKs/índices; contratos validados por testes; OpenAPI e cliente frontend sincronizados; nenhum endpoint retorna dados de outro cliente.
