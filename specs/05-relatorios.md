# SPEC-05 — Relatórios e exportação PDF

## Funcionalidades
- Criar relatório para cliente com título, período, fontes, KPIs, gráficos, comentários e template.
- Visualizar preview antes de gerar; salvar configuração para reuso.
- Geração PDF assíncrona em worker, com estado `pendente/processando/concluido/erro` e progresso/erro seguro.
- Histórico de execuções e download autenticado; arquivos em storage privado com retenção configurável.
- Versão inicial: templates Visão Executiva e Performance de Campanhas.

## API
`GET/POST /relatorios`, `GET/PATCH/DELETE /relatorios/{id}`, `POST /relatorios/{id}/gerar`, `GET /relatorios/{id}/execucoes`, `GET /relatorios/execucoes/{execucao_id}/download`.

## Regras
A geração captura filtros, período, horário de corte e timestamp da última coleta. Não enviar automaticamente ao cliente; não criar links públicos no MVP. A execução é idempotente quando a mesma solicitação é repetida com mesma chave; não expor caminhos internos da VPS.

## Critérios de aceite
PDF legível em A4, sem cortes em tabelas/gráficos; números correspondem ao dashboard no mesmo snapshot; falha é recuperável; download só funciona para colaboradores autorizados; histórico preservado após arquivamento do cliente.
