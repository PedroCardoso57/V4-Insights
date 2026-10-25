# SPEC-06 — Frontend e experiência

## Rotas/telas
- `/login`: botão Entrar com Google e tratamento de acesso negado.
- `/`: visão geral interna, clientes atribuídos, alertas de sincronização e atalhos.
- `/clientes`: lista, busca, filtros e modal de cadastro/edição/arquivamento.
- `/clientes/[id]`: detalhes, equipe, integrações e indicadores.
- `/clientes/[id]/dashboards`: filtros, cards e gráficos.
- `/relatorios`: lista, editor, preview e execuções.
- `/integracoes`: conexões, contas, status e reprocessamento.
- `/usuarios`: administração de contas e permissões (somente admin).
- `/configuracoes`: preferências internas e status operacional permitido.

## Padrões
Next.js App Router, TypeScript strict, TanStack Query para cache de servidor, React Hook Form + Zod, Tailwind/shadcn/ui, Recharts; componentes reutilizáveis. Layout com sidebar, breadcrumb, seletor de cliente e estado de atualização. Responsivo a partir de 360px. Acessibilidade: navegação por teclado, labels, foco visível, contraste adequado.

## Interações
Criar/editar/excluir lógico por modal com confirmação; loading skeleton; erro com retry; empty state orientativo; feedback de sucesso sem mensagens falsas. A UI oculta ações sem permissão, mas a API aplica a autorização real.

## Critérios de aceite
Fluxos de login, cliente, conexão, dashboard e PDF navegáveis; testes E2E para fluxos críticos; nenhuma credencial aparece no bundle frontend; funcionamento em desktop e mobile.
