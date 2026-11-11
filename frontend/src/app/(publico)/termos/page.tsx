import type { Metadata } from "next";
import Link from "next/link";

import { DocumentoLegal } from "@/components/documento-legal";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = { title: "Termos de uso" };

export default function TermosPage() {
  return (
    <DocumentoLegal
      titulo="Termos de uso"
      resumo={
        <>
          O {LEGAL.produto} é uma ferramenta interna da {LEGAL.controlador}. Ao usá-lo, você concorda com as regras abaixo.
        </>
      }
    >
      <section>
        <h2>Quem pode usar</h2>
        <p>
          Apenas colaboradores cadastrados por um administrador da {LEGAL.controlador}. Não há cadastro público. O acesso é
          pessoal e intransferível, e pode ser suspenso a qualquer momento.
        </p>
      </section>

      <section>
        <h2>Conexão de contas de anúncio</h2>
        <p>
          Ao conectar uma conta da Meta, Google Ads, LinkedIn ou TikTok, você declara ter autorização do titular da conta
          para que o {LEGAL.produto} leia as métricas de campanhas. O acesso é somente leitura: a plataforma não cria, altera
          nem pausa anúncios. A conexão pode ser revogada a qualquer momento na tela Integrações ou nas configurações da
          própria plataforma de anúncios.
        </p>
      </section>

      <section>
        <h2>Uso adequado</h2>
        <ul>
          <li>Usar os dados apenas para atender os clientes da sua carteira.</li>
          <li>Não compartilhar senha, sessão ou relatórios com quem não tem direito de acesso.</li>
          <li>Não tentar acessar dados de clientes fora da sua carteira nem contornar controles de segurança.</li>
        </ul>
        <p>As ações na plataforma ficam registradas para fins de segurança e auditoria.</p>
      </section>

      <section>
        <h2>Números exibidos</h2>
        <p>
          As métricas vêm das APIs das plataformas e podem mudar quando a própria plataforma ajusta dados de dias recentes.
          Cada dashboard e relatório mostra quando os dados foram atualizados pela última vez.
        </p>
      </section>

      <section>
        <h2>Privacidade</h2>
        <p>
          O tratamento de dados pessoais segue a <Link href="/privacidade">Política de privacidade</Link>. Dúvidas:{" "}
          <a href={`mailto:${LEGAL.contato}`}>{LEGAL.contato}</a>.
        </p>
      </section>
    </DocumentoLegal>
  );
}
