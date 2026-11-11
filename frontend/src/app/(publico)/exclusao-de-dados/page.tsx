import type { Metadata } from "next";
import Link from "next/link";

import { DocumentoLegal } from "@/components/documento-legal";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = { title: "Exclusão de dados" };

export default function ExclusaoDeDadosPage() {
  return (
    <DocumentoLegal
      titulo="Exclusão de dados"
      resumo={
        <>
          Você pode apagar a qualquer momento os dados que o {LEGAL.produto} recebeu de uma conta de anúncio, ou os seus
          próprios dados de acesso. Escolha o caminho abaixo.
        </>
      }
    >
      <section>
        <h2>Desconectar uma conta da Meta (Facebook e Instagram)</h2>
        <ol>
          <li>
            No Facebook, abra <strong>Configurações e privacidade</strong>, depois <strong>Configurações</strong> e{" "}
            <strong>Aplicativos e sites</strong>.
          </li>
          <li>
            Encontre <strong>{LEGAL.produto}</strong> e clique em <strong>Remover</strong>.
          </li>
          <li>
            Isso cancela o acesso na hora. Para apagar também o que já foi coletado, envie o pedido descrito no fim desta
            página.
          </li>
        </ol>
      </section>

      <section>
        <h2>Desconectar pelo próprio {LEGAL.produto}</h2>
        <p>
          Quem tem acesso à plataforma pode abrir o cliente, ir em <strong>Integrações</strong> e clicar em{" "}
          <strong>Revogar</strong>. O token de acesso é apagado no mesmo momento e nenhuma coleta nova acontece.
        </p>
      </section>

      <section>
        <h2>Google Ads, LinkedIn e TikTok</h2>
        <p>
          O acesso também pode ser removido na conta de cada plataforma, na área de apps ou permissões conectadas: Google
          (myaccount.google.com, em Segurança, Conexões com apps de terceiros), LinkedIn (Configurações, Dados e privacidade)
          e TikTok for Business (Configurações, Apps autorizados).
        </p>
      </section>

      <section>
        <h2>Pedir a exclusão completa</h2>
        <p>
          Escreva para <a href={`mailto:${LEGAL.contato}?subject=Exclus%C3%A3o%20de%20dados`}>{LEGAL.contato}</a> com o
          assunto <strong>Exclusão de dados</strong>, informando o nome ou o identificador da conta de anúncio, ou o e-mail
          usado no login. Apagamos as métricas, os nomes de campanhas e os tokens ligados a ela, ou anonimizamos seus dados
          de acesso, e confirmamos por e-mail em até {LEGAL.prazoRespostaDias} dias. Registros de auditoria são mantidos sem
          identificação pessoal, conforme a <Link href="/privacidade">Política de privacidade</Link>.
        </p>
      </section>
    </DocumentoLegal>
  );
}
