BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE perfis (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 codigo varchar(32) NOT NULL UNIQUE CHECK (codigo IN ('admin','gestor','analista','visualizador')),
 nome varchar(80) NOT NULL
);
INSERT INTO perfis(codigo,nome) VALUES ('admin','Administrador'),('gestor','Gestor'),('analista','Analista'),('visualizador','Visualizador');
CREATE TABLE usuarios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 perfil_id uuid NOT NULL REFERENCES perfis(id),
 google_sub varchar(255) UNIQUE,
 nome varchar(180) NOT NULL,
 email varchar(320) NOT NULL,
 ativo boolean NOT NULL DEFAULT true,
 criado_em timestamptz NOT NULL DEFAULT now(),
 atualizado_em timestamptz NOT NULL DEFAULT now(),
 ultimo_login_em timestamptz
);
CREATE UNIQUE INDEX uq_usuarios_email_lower ON usuarios(lower(email));
CREATE TABLE clientes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 nome varchar(180) NOT NULL,
 nome_fantasia varchar(180),
 documento varchar(20),
 status varchar(24) NOT NULL DEFAULT 'ativo' CHECK(status IN ('ativo','inativo')),
 criado_em timestamptz NOT NULL DEFAULT now(),
 atualizado_em timestamptz NOT NULL DEFAULT now(),
 arquivado_em timestamptz
);
CREATE TABLE usuarios_clientes (
 usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 cliente_id uuid NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
 criado_em timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(usuario_id,cliente_id)
);
CREATE TABLE integracoes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 cliente_id uuid NOT NULL REFERENCES clientes(id),
 plataforma varchar(32) NOT NULL CHECK(plataforma IN ('meta_ads','google_ads')),
 identificador_externo varchar(255),
 status varchar(32) NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','conectada','erro','revogada')),
 referencia_credencial varchar(255),
 ultima_sincronizacao_em timestamptz,
 erro_sincronizacao text,
 criado_em timestamptz NOT NULL DEFAULT now(),
 atualizado_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_integracoes_cliente ON integracoes(cliente_id);
CREATE TABLE contas_anuncio (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 integracao_id uuid NOT NULL REFERENCES integracoes(id),
 conta_externa_id varchar(255) NOT NULL,
 nome varchar(255) NOT NULL,
 moeda char(3) NOT NULL DEFAULT 'BRL',
 fuso_horario varchar(100) NOT NULL DEFAULT 'America/Sao_Paulo',
 ativa boolean NOT NULL DEFAULT true,
 UNIQUE(integracao_id,conta_externa_id)
);
CREATE TABLE metricas_diarias (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 conta_anuncio_id uuid NOT NULL REFERENCES contas_anuncio(id),
 data date NOT NULL,
 nivel varchar(24) NOT NULL CHECK(nivel IN ('conta','campanha','conjunto','anuncio')),
 entidade_externa_id varchar(255) NOT NULL,
 impressoes bigint NOT NULL DEFAULT 0,
 cliques bigint NOT NULL DEFAULT 0,
 investimento numeric(18,4) NOT NULL DEFAULT 0,
 conversoes numeric(18,4) NOT NULL DEFAULT 0,
 valor_conversoes numeric(18,4) NOT NULL DEFAULT 0,
 dados_extras jsonb NOT NULL DEFAULT '{}'::jsonb,
 sincronizado_em timestamptz NOT NULL DEFAULT now(),
 UNIQUE(conta_anuncio_id,data,nivel,entidade_externa_id)
);
CREATE INDEX ix_metricas_conta_data ON metricas_diarias(conta_anuncio_id,data DESC);
CREATE TABLE dashboards (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 cliente_id uuid NOT NULL REFERENCES clientes(id),
 criado_por uuid NOT NULL REFERENCES usuarios(id),
 nome varchar(180) NOT NULL,
 configuracao jsonb NOT NULL DEFAULT '{}'::jsonb,
 criado_em timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE dashboard_widgets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 dashboard_id uuid NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
 tipo varchar(60) NOT NULL,
 posicao integer NOT NULL DEFAULT 0,
 configuracao jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE relatorios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 cliente_id uuid NOT NULL REFERENCES clientes(id),
 criado_por uuid NOT NULL REFERENCES usuarios(id),
 titulo varchar(180) NOT NULL,
 configuracao jsonb NOT NULL DEFAULT '{}'::jsonb,
 criado_em timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE relatorio_execucoes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 relatorio_id uuid NOT NULL REFERENCES relatorios(id),
 status varchar(24) NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','processando','concluido','erro')),
 arquivo_referencia text,
 erro text,
 iniciado_em timestamptz NOT NULL DEFAULT now(),
 finalizado_em timestamptz
);
CREATE TABLE auditoria (
 id bigserial PRIMARY KEY,
 usuario_id uuid REFERENCES usuarios(id) ON DELETE SET NULL,
 acao varchar(100) NOT NULL,
 entidade varchar(80) NOT NULL,
 entidade_id uuid,
 metadados jsonb NOT NULL DEFAULT '{}'::jsonb,
 data_hora timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_auditoria_data ON auditoria(data_hora DESC);
COMMIT;
