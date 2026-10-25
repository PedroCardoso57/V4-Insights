# SPEC-00 — Fundação técnica

## Objetivo
Criar projeto reproduzível para desenvolvimento, homologação e produção em VPS.

## Requisitos
- Monorepo frontend/backend/infra/specs, Python 3.12+, Node LTS, dependências travadas por lockfile.
- API com `/health/live` (processo) e `/health/ready` (banco/Redis, quando necessário); readiness falha com 503 se dependências críticas indisponíveis.
- Configuração via ambiente validada na inicialização; `.env.example` sem segredos reais.
- Compose com serviços `frontend`, `api`, `worker`, `redis`, `postgres`, `proxy`; banco e Redis sem publicação de portas externas.
- Alembic como fonte de versionamento; incorporar baseline SQL existente com cautela para ambientes já migrados.
- Pipeline CI: lint, typecheck, testes, build e verificação de migrations.
- README com pré-requisitos, setup, comandos, troubleshooting e deploy.

## Critérios de aceite
1. `docker compose up --build` inicializa serviços com health checks.
2. `GET /health/live` retorna 200 e `/health/ready` detecta falha real de banco.
3. Ambiente limpo aplica migrations uma única vez; repetição não duplica tabelas.
4. Nenhum segredo é comitado; builds reproduzíveis e rollback documentado.

## Dependências
Nenhuma. Entrega inicial obrigatória para demais módulos.
