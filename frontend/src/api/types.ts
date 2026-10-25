export type Papel = "admin" | "gestor" | "analista" | "visualizador";
export type Plataforma = "meta" | "google_ads";
export type Nivel = "campanha" | "conjunto" | "anuncio";
export type Granularidade = "dia" | "semana" | "mes";

export interface Me {
  id: string;
  nome: string;
  email: string;
  papel: Papel;
  csrf_token: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  papel: Papel;
  ativo: boolean;
  vinculado_google: boolean;
  ultimo_login_em: string | null;
  criado_em: string;
}

export interface Cliente {
  id: string;
  nome: string;
  nome_fantasia: string | null;
  documento: string | null;
  status: "ativo" | "arquivado";
  criado_em: string;
  atualizado_em: string;
  arquivado_em: string | null;
}

export interface Membro {
  id: string;
  nome: string;
  email: string;
  papel: Papel;
  ativo: boolean;
  atribuido_em: string;
}

export interface Conta {
  id: string;
  id_externo: string;
  nome: string;
  moeda: string | null;
  fuso: string | null;
  ativa: boolean;
  carga_historica_dias: number;
  mapeamento_conversoes: { action_types?: string[]; janela?: string };
  ultima_sincronizacao_em: string | null;
  dados_ate: string | null;
}

export interface Integracao {
  id: string;
  cliente_id: string;
  plataforma: Plataforma;
  status: "pendente" | "ativa" | "pausada" | "erro" | "revogada";
  escopos: string[];
  ultimo_erro: string | null;
  criado_em: string;
  atualizado_em: string;
  revogada_em: string | null;
  contas: Conta[];
}

export interface ContaDisponivel {
  id_externo: string;
  nome: string;
  moeda: string | null;
  fuso: string | null;
  selecionada: boolean;
}

export interface SyncJob {
  id: string;
  conta_anuncio_id: string;
  tipo: string;
  status: string;
  data_inicio: string;
  data_fim: string;
  linhas: number;
  tentativas: number;
  erro: string | null;
  iniciado_em: string | null;
  finalizado_em: string | null;
  proxima_tentativa_em: string | null;
  criado_em: string;
}

// Valores decimais chegam como string para preservar precisão.
export interface Kpis {
  investimento: string | null;
  impressoes: number | null;
  cliques: number | null;
  conversoes: string | null;
  valor_conversoes: string | null;
  ctr: string | null;
  cpc: string | null;
  cpm: string | null;
  cpa: string | null;
  roas: string | null;
}
export type KpiKey = keyof Kpis;

export interface Resumo {
  periodo: { inicio: string; fim: string };
  periodo_anterior: { inicio: string; fim: string } | null;
  atual: Kpis;
  anterior: Kpis | null;
  variacao_percentual: Record<KpiKey, string | null>;
  moedas: string[];
  ultima_sincronizacao_em: string | null;
  integracoes_conectadas: number;
  nivel: Nivel;
}

export interface PontoSerie {
  periodo: string;
  kpis: Kpis;
}

export interface Serie {
  granularidade: Granularidade;
  pontos: PontoSerie[];
  comparacao: PontoSerie[] | null;
}

export interface Campanha {
  plataforma: Plataforma;
  conta_anuncio_id: string;
  campanha_externa_id: string;
  campanha_nome: string | null;
  kpis: Kpis;
}

export type WidgetTipo = "kpi" | "serie" | "tabela_campanhas";

export interface Widget {
  id?: string;
  tipo: WidgetTipo;
  titulo: string;
  config: { kpi?: KpiKey };
  posicao: Record<string, unknown>;
  ordem: number;
}

export interface Dashboard {
  id: string;
  cliente_id: string;
  nome: string;
  descricao: string | null;
  filtros: Partial<Filtros>;
  layout: Record<string, unknown>;
  criado_em: string;
  atualizado_em: string;
  widgets: Widget[];
}

export interface Filtros {
  inicio: string;
  fim: string;
  plataforma: Plataforma | "";
  conta_anuncio_id: string;
  campanha_id: string;
  granularidade: Granularidade;
  comparar: boolean;
}

export interface Auditoria {
  id: number;
  usuario_id: string | null;
  acao: string;
  entidade: string;
  entidade_id: string | null;
  cliente_id: string | null;
  dados: Record<string, unknown>;
  criado_em: string;
}
