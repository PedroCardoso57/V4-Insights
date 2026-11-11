import type { Metadata } from "next";
import Link from "next/link";

import { DocumentoLegal } from "@/components/documento-legal";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = { title: "Política de privacidade" };

export default function PrivacidadePage() {
  return (
    <DocumentoLegal
      titulo="Política de privacidade"
      resumo={
        <>
          O {LEGAL.produto} é a plataforma interna da {LEGAL.controlador} para acompanhar o desempenho de campanhas de
          anúncios dos seus clientes. Esta página explica quais dados tratamos, para quê e como pedir acesso ou exclusão.
        </>
      }
    >
      <section>
        <h2>Quem é o controlador</h2>
        <p>
          A <strong>{LEGAL.controlador}</strong>, unidade franqueada da V4 Company, é a controladora dos dados tratados no{" "}
          {LEGAL.produto} ({LEGAL.site}). Dúvidas e pedidos sobre dados pessoais: <a href={`mailto:${LEGAL.contato}`}>{LEGAL.contato}</a>.
        </p>
      </section>

      <section>
        <h2>Dados que tratamos</h2>
        <ul>
          <li>
            <strong>Colaboradores da {LEGAL.controlador}:</strong> nome, e-mail, perfil de acesso, foto de perfil opcional,
            identificador da conta Google usada no login, hash da senha (quando há login por senha), endereço IP e
            navegador das sessões e o registro das ações feitas na plataforma.
          </li>
          <li>
            <strong>Clientes da {LEGAL.controlador}:</strong> nome, nome fantasia e, opcionalmente, CPF ou CNPJ.
          </li>
          <li>
            <strong>Contas de anúncio conectadas</strong> (Meta, Google Ads, LinkedIn e TikTok): identificador, nome, moeda e
            fuso das contas, nomes e identificadores de campanhas, e métricas agregadas por dia, como investimento,
            impressões, cliques e conversões. Também guardamos, cifrado, o token de acesso que a pessoa concedeu ao
            conectar a conta.
          </li>
        </ul>
        <p>
          Não coletamos dados das pessoas que viram ou clicaram nos anúncios. As plataformas entregam apenas números
          agregados, sem identificar ninguém.
        </p>
      </section>

      <section>
        <h2>Para que usamos</h2>
        <ul>
          <li>Autenticar colaboradores e controlar quem acessa cada cliente.</li>
          <li>Coletar e exibir as métricas das campanhas em dashboards e relatórios em PDF.</li>
          <li>Manter a segurança da plataforma e um registro de auditoria das ações sensíveis.</li>
        </ul>
        <p>
          Os dados obtidos pelas APIs das plataformas de anúncio são usados apenas para esses relatórios. Não vendemos,
          não compartilhamos com terceiros para publicidade e não usamos esses dados para treinar modelos.
        </p>
      </section>

      <section>
        <h2>Base legal</h2>
        <p>
          Execução do contrato de prestação de serviços com os clientes, legítimo interesse na segurança e na gestão da
          operação, e cumprimento de obrigações legais, conforme a Lei 13.709/2018 (LGPD).
        </p>
      </section>

      <section>
        <h2>Por quanto tempo guardamos</h2>
        <ul>
          <li>Dados de colaboradores: enquanto a conta estiver ativa, com anonimização sob pedido ou no desligamento.</li>
          <li>Sessões: até 30 dias depois de expirarem. Registro de auditoria: até 2 anos.</li>
          <li>PDFs de relatórios: 90 dias.</li>
          <li>Tokens das plataformas: até a conexão ser revogada, quando são apagados.</li>
        </ul>
      </section>

      <section>
        <h2>Como protegemos</h2>
        <p>
          Conexão sempre por HTTPS, tokens e chaves cifrados no banco com chave guardada fora dele, acesso por perfil e por
          carteira de clientes, registros sem segredos, limite de tentativas de login e backups cifrados.
        </p>
      </section>

      <section>
        <h2>Seus direitos</h2>
        <p>
          Você pode pedir confirmação de tratamento, acesso, correção, portabilidade, anonimização ou exclusão dos seus
          dados escrevendo para <a href={`mailto:${LEGAL.contato}`}>{LEGAL.contato}</a>. Respondemos em até{" "}
          {LEGAL.prazoRespostaDias} dias. Para apagar os dados de uma conta de anúncio conectada, veja{" "}
          <Link href="/exclusao-de-dados">Exclusão de dados</Link>.
        </p>
      </section>

      <section>
        <h2>Mudanças nesta política</h2>
        <p>Quando esta política mudar, a data de revisão no rodapé é atualizada. Última revisão: {LEGAL.revisadoEm}.</p>
      </section>
    </DocumentoLegal>
  );
}
