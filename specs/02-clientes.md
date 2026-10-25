# SPEC-02 — Clientes e carteiras

## Entidades
`clientes`: id UUID, nome, nome_fantasia, documento opcional, status, criado_em, atualizado_em, arquivado_em. `usuarios_clientes`: usuario_id, cliente_id, criado_em, chave composta.

## Funcionalidades
- Lista com busca por nome, filtros ativo/arquivado, paginação e ordenação.
- Cadastro e edição com validação de tamanho, campos obrigatórios e normalização de documento quando informado.
- Arquivamento com confirmação em modal, sem excluir métricas ou relatórios.
- Associação e remoção de colaboradores à carteira; mostrar integrantes autorizados.
- Tela de detalhes com abas Visão geral, Integrações, Dashboards, Relatórios e Equipe.
- Registro de auditoria em criar, editar, arquivar e alterar acessos.

## Endpoints
`GET /clientes?search=&status=&page=&page_size=`, `POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/arquivar`, `GET /clientes/{id}/usuarios`.

## Regras
- Nunca retornar cliente não autorizado em listagens; consulta por ID alheio responde 404 para não revelar existência.
- Não permitir criar integrações para cliente arquivado.
- Não excluir registros vinculados ao arquivar.

## Critérios de aceite
CRUD e busca funcionam, arquivamento preserva histórico, paginação é estável e dois usuários de carteiras diferentes não acessam os dados um do outro.
