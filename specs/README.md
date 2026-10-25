# V4 Insights — Especificações de Implementação

**Unidade:** V4 Bounnacorso  
**Versão:** 1.0 — 24/10/2026  
**Status:** Proposta técnica para implementação; validar com a equipe  
**Público:** colaboradores internos exclusivamente

## 1. Visão e limites

Plataforma interna de gestão de clientes, integração de contas Meta Ads e Google Ads, visualização de KPIs e elaboração de relatórios. Referências funcionais: Reportei e ReportHero, sem replicar código, marca ou identidade visual de terceiros.

**Incluído no MVP:** login Google OIDC por convite/pré-cadastro, quatro papéis, carteira de clientes, conexão e sincronização das duas fontes, dashboards filtráveis, geração de PDF, histórico de execução, auditoria e deploy em VPS.

**Fora do MVP:** portal de cliente, multi-franquia, cobrança, envio automático por WhatsApp, IA generativa, gestão de campanhas/edição em provedores, conectores adicionais e white-label.

## 2. Arquitetura

- Frontend: Next.js + TypeScript + Tailwind + shadcn/ui + Recharts.
- API: FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic; monólito modular.
- Dados: PostgreSQL 16+, Redis para filas/cache; Celery para jobs.
- Deploy: VPS Linux com Docker Compose, reverse proxy TLS, volumes persistentes e backup externo criptografado.
- API versionada em `/api/v1`, JSON UTF-8; horários de eventos em UTC e datas de métricas no fuso da conta.
- Login: Google OAuth 2.0 / OpenID Connect, autorização por usuário previamente cadastrado, sem cadastro público.
- Integrações: Meta Marketing API e Google Ads API, com permissões/credenciais aprovadas pelos provedores; nenhum token em logs.

Fluxo: navegador → proxy HTTPS → frontend/API → PostgreSQL; API → Redis/Celery → APIs externas → métricas normalizadas → dashboards/relatórios.

## 3. Estrutura de repositório

```text
v4-insights/
  frontend/src/{app,components,features,services,hooks}/
  backend/app/{api,core,db,models,schemas,services,integrations,workers}/
  backend/alembic/versions/
  backend/tests/{unit,integration}/
  infra/{docker,proxy,backup}/
  docs/
  specs/
  docker-compose.yml
  .env.example
  README.md
```

## 4. Especificações por módulo

| ID | Módulo | Arquivo | Prioridade |
|---|---|---|---|
| SPEC-00 | Fundação e infraestrutura | [00-fundacao.md](00-fundacao.md) | P0 |
| SPEC-01 | Identidade e RBAC | [01-autenticacao-rbac.md](01-autenticacao-rbac.md) | P0 |
| SPEC-02 | Clientes e carteiras | [02-clientes.md](02-clientes.md) | P0 |
| SPEC-03 | Integrações e coleta | [03-integracoes.md](03-integracoes.md) | P0 |
| SPEC-04 | Métricas e dashboards | [04-dashboards.md](04-dashboards.md) | P0 |
| SPEC-05 | Relatórios e PDF | [05-relatorios.md](05-relatorios.md) | P0 |
| SPEC-06 | Frontend e UX | [06-frontend.md](06-frontend.md) | P0 |
| SPEC-07 | Qualidade, segurança e deploy | [07-qualidade-deploy.md](07-qualidade-deploy.md) | P0 |
| SPEC-08 | Banco e contratos | [08-dados-api.md](08-dados-api.md) | P0 |
| SPEC-09 | Plano de execução | [09-backlog.md](09-backlog.md) | P0 |

## 5. Regras transversais

1. Todos os endpoints de negócio exigem sessão autenticada e verificação de autorização no servidor.
2. Acesso a clientes depende de vínculo em `usuarios_clientes`, exceto administrador; gestor não acessa automaticamente clientes fora de sua carteira.
3. Não há criação de usuários por autoinscrição; administrador cadastra e atribui perfil.
4. Excluir cliente = arquivar (soft delete); preservar histórico e registros necessários à auditoria.
5. Operações de sincronização e geração de PDF são assíncronas, com estados e idempotência.
6. Nunca expor tokens de provedores ou segredos em respostas, logs, banco em texto puro ou repositório.
7. Todos os fluxos de erro devem apresentar mensagem útil e identificador de correlação.
8. Qualquer mudança de schema exige migration reversível quando tecnicamente possível e testes.

## 6. Definição global de pronto (DoD)

- Código revisado e tipado, migrations versionadas, testes automatizados passando e lint sem erros.
- Controle de acesso coberto por testes de permissão e isolamento entre clientes.
- Swagger/OpenAPI atualizado, erros documentados, auditoria em ações sensíveis.
- Tela funcional em desktop e mobile, com loading, vazio, erro e sucesso.
- Logs estruturados, health checks, backup e procedimento de rollback disponíveis.
- Demonstração em homologação e aceite do responsável funcional.

## 7. Compatibilidade com o pacote inicial

O pacote `V4_Insights_Fundacao_Sprint1.zip` já possui `backend/migrations/001_initial.sql`, tabelas base, rotas de autenticação e clientes. **Não considerar esses arquivos prontos para produção**. Esta especificação exige revisar especialmente a segurança das sessões/CSRF, completude do CRUD, escopo de acesso por cliente, migrations versionadas, testes e operacionalização das integrações.

## 8. Pendências de produto

Confirmar a lista exata de KPIs por plataforma, metas e convenções de conversão, periodicidade desejada da atualização, layout/identidade visual oficial da unidade, política de retenção e número esperado de contas/usuários. Adotar defaults documentados até aprovação; não inventar métricas equivalentes entre provedores.
