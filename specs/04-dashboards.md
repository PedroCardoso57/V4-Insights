# SPEC-04 — Métricas e dashboards

## KPIs
Investimento, impressões, cliques, CTR, CPC, CPM, conversões, custo por conversão e ROAS quando houver valor de conversões confiável. Fórmulas: CTR=100*cliques/impressões; CPC=investimento/cliques; CPM=1000*investimento/impressões; CPA=investimento/conversões; ROAS=valor_conversoes/investimento. Divisão por zero resulta em valor ausente, nunca infinito.

## Filtros
Cliente obrigatório, plataforma, conta, campanha (quando disponível), período customizado, comparação com período anterior e granularidade diária/semanal/mensal.

## Telas
Visão geral por cliente; cards de KPI com variação percentual; séries temporais; tabela de campanhas ordenável; estado vazio quando integração não conectada; aviso de última sincronização; criação/edição de widgets e dashboards por perfil.

## API
`GET /clientes/{id}/metricas/resumo`, `GET /clientes/{id}/metricas/serie`, `GET /clientes/{id}/campanhas`, `GET/POST /dashboards`, `GET/PATCH/DELETE /dashboards/{id}`, `POST /dashboards/{id}/widgets`.

## Modelo
`metricas_diarias` armazena dados base e JSONB de campos específicos; dashboard/widgets armazenam layout e filtros. Para somas agregadas usar somente um nível por consulta, evitando contar campanha+anúncio simultaneamente. Considerar conversões por tipo e atribuição em tabela/JSON normalizado, antes de prometer equivalência cross-channel.

## Critérios de aceite
Filtros alteram todos os gráficos de forma consistente; dados batem com fixtures e arredondamento definido; conta sem dados mostra vazio; comparativos e percentuais não dividem por zero; carteira de outro colaborador é inacessível.
