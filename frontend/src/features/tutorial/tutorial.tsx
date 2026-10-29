"use client";

import { ArrowLeftIcon, ArrowRightIcon, XIcon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { urlNico } from "@/components/avatar";
import { Button } from "@/components/ui/button";
import { useMarcarTutorial } from "@/features/tutorial/api";
import { useClienteAtual } from "@/hooks/use-cliente-atual";
import { useMe } from "@/hooks/use-me";
import type { Papel } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { cn } from "@/lib/utils";

interface Passo {
  titulo: string;
  texto: string;
  /** Pose do Nico (public/mascote/avatares). */
  nico: string;
  /** `data-tour` do elemento destacado; sem alvo visível, o balão fica no centro. */
  alvo?: string;
  /** Página aberta por trás do balão enquanto o passo é explicado. */
  rota?: string;
}

export function passosDoTutorial(nome: string, papel: Papel | undefined, clienteAtual: string | null): Passo[] {
  const primeiroNome = nome.trim().split(/\s+/)[0] ?? "";
  const passos: (Passo | false)[] = [
    {
      titulo: `Oi, ${primeiroNome}! Eu sou o Nico.`,
      texto: "Sou o Nico do V4 Insights e vou te mostrar como o sistema funciona em menos de um minuto. Dá para pular quando quiser.",
      nico: "parado",
    },
    {
      titulo: "Visão geral",
      texto: "Seu ponto de partida: os clientes da sua carteira, o status das integrações e os alertas que pedem atenção.",
      nico: "notebook",
      alvo: "nav:Visão geral",
      rota: "/",
    },
    {
      titulo: "Cliente em foco",
      texto: "Escolha aqui o cliente que você quer analisar. Os dashboards abrem sempre no cliente selecionado.",
      nico: "correndo",
      alvo: "cliente",
    },
    {
      titulo: "Clientes",
      texto: pode.gerirClientes(papel)
        ? "A carteira de clientes, com os responsáveis e as integrações de cada um. É por aqui que você cadastra um cliente novo."
        : "A carteira com os clientes atribuídos a você, os responsáveis e as integrações de cada um.",
      nico: "bracos-cruzados",
      alvo: "nav:Clientes",
      rota: "/clientes",
    },
    {
      titulo: "Dashboards",
      texto: "As métricas de Meta, Google, LinkedIn e TikTok Ads do cliente em foco, com filtros de período, gráficos e campanhas.",
      nico: "servidores",
      alvo: "nav:Dashboards",
      rota: clienteAtual ? `/clientes/${clienteAtual}/dashboards` : undefined,
    },
    {
      titulo: "Relatórios",
      texto: "Monte o relatório do cliente, confira a prévia e gere o PDF pronto para enviar.",
      nico: "notebook",
      alvo: "nav:Relatórios",
      rota: "/relatorios",
    },
    pode.editar(papel) && {
      titulo: "Integrações",
      texto: "Conecte as contas de anúncio de cada cliente. Quando uma conexão precisar ser refeita, aparece um número vermelho aqui no menu.",
      nico: "engrenagem",
      alvo: "nav:Integrações",
      rota: "/integracoes",
    },
    pode.gerirUsuarios(papel) && {
      titulo: "Usuários",
      texto: "Não há autocadastro: aqui você cadastra os colaboradores e define o perfil de acesso de cada um.",
      nico: "bracos-cruzados",
      alvo: "nav:Usuários",
      rota: "/usuarios",
    },
    {
      titulo: "Configurações e seu perfil",
      texto: "Troque sua foto (pode ser um Nico!), a senha, o tema e as preferências dos dashboards.",
      nico: "engrenagem",
      alvo: "nav:Configurações",
      rota: "/configuracoes",
    },
    {
      titulo: "Pronto, agora é com você!",
      texto: "Bom trabalho! Agora é só explorar o V4 Insights.",
      nico: "comemorando",
      rota: "/",
    },
  ];
  return passos.filter((p): p is Passo => p !== false);
}

const LARGURA = 360;
const MARGEM = 16;
const FOLGA = 6;

interface Caixa {
  top: number;
  left: number;
  width: number;
  height: number;
}

function caixaDoAlvo(alvo?: string): Caixa | null {
  if (!alvo) return null;
  // O mesmo alvo pode existir no menu lateral e na barra inferior do celular: vale o que está visível.
  const r = Array.from(document.querySelectorAll<HTMLElement>(`[data-tour="${CSS.escape(alvo)}"]`))
    .map((el) => el.getBoundingClientRect())
    .find((c) => c.width > 0 && c.height > 0);
  if (!r) return null;
  return { top: r.top - FOLGA, left: r.left - FOLGA, width: r.width + FOLGA * 2, height: r.height + FOLGA * 2 };
}

/** Ao lado do alvo quando cabe (menu lateral), senão abaixo dele (cabeçalho) ou acima (barra inferior); sem alvo, no centro. */
function posicaoDoBalao(alvo: Caixa | null, altura: number): { top: number; left: number } {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const largura = Math.min(LARGURA, vw - MARGEM * 2);
  const limitar = (v: number, max: number) => Math.max(MARGEM, Math.min(v, max));
  if (!alvo) return { top: limitar((vh - altura) / 2, vh - altura - MARGEM), left: (vw - largura) / 2 };
  if (alvo.left + alvo.width + MARGEM + largura < vw - MARGEM) {
    return {
      top: limitar(alvo.top + alvo.height / 2 - altura / 2, vh - altura - MARGEM),
      left: alvo.left + alvo.width + MARGEM,
    };
  }
  // Alvo perto do rodapé (barra inferior do celular): o balão fica acima dele.
  const cabeAbaixo = alvo.top + alvo.height + MARGEM + altura <= vh - MARGEM;
  return {
    top: cabeAbaixo ? alvo.top + alvo.height + MARGEM : limitar(alvo.top - MARGEM - altura, vh - altura - MARGEM),
    left: limitar(alvo.left + alvo.width / 2 - largura / 2, vw - largura - MARGEM),
  };
}

/**
 * Tutorial de primeiro acesso: o Nico apresenta cada área do sistema, destacando o item
 * do menu e abrindo a página por trás. Aparece enquanto a sessão diz que o colaborador
 * ainda não o viu; concluir ou pular grava isso no servidor (vale para qualquer navegador).
 */
export function Tutorial() {
  const me = useMe().data;
  const [clienteAtual] = useClienteAtual();
  const marcar = useMarcarTutorial();
  const router = useRouter();
  const path = usePathname();
  const [indice, setIndice] = useState(0);
  const [alvo, setAlvo] = useState<Caixa | null>(null);
  const [posicao, setPosicao] = useState<{ top: number; left: number } | null>(null);
  const balao = useRef<HTMLDivElement>(null);
  const aberto = me?.tutorial_visto === false;
  const passos = me ? passosDoTutorial(me.nome, me.papel, clienteAtual) : [];
  const passo = passos[Math.min(indice, passos.length - 1)];
  const ultimo = indice >= passos.length - 1;

  const fechar = useCallback(() => {
    marcar.mutate(true);
    setIndice(0);
  }, [marcar]);

  // Abre a página do passo por trás do balão.
  useEffect(() => {
    if (aberto && passo?.rota && passo.rota !== path) router.push(passo.rota);
  }, [aberto, passo?.rota, path, router]);

  // Mede o alvo e o balão a cada passo, troca de página, rolagem ou redimensionamento.
  const alvoId = passo?.alvo;
  useLayoutEffect(() => {
    if (!aberto) return;
    const medir = () => {
      const caixa = caixaDoAlvo(alvoId);
      setAlvo(caixa);
      setPosicao(posicaoDoBalao(caixa, balao.current?.offsetHeight ?? 240));
    };
    medir();
    // A página nova pode demorar um instante para montar o menu e o cabeçalho.
    const id = window.setTimeout(medir, 120);
    window.addEventListener("resize", medir);
    window.addEventListener("scroll", medir, true);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("resize", medir);
      window.removeEventListener("scroll", medir, true);
    };
  }, [aberto, alvoId, indice, path]);

  useEffect(() => {
    if (aberto) balao.current?.focus();
  }, [aberto, indice]);

  if (!aberto || !passo) return null;

  const avancar = () => (ultimo ? fechar() : setIndice(indice + 1));
  const voltar = () => setIndice(Math.max(0, indice - 1));

  return (
    <div className="fixed inset-0 z-[70]" data-testid="tutorial">
      {alvo ? (
        // O "buraco" no escurecimento é uma sombra gigante ao redor do item destacado.
        <div
          aria-hidden
          className="pointer-events-none fixed rounded-xl ring-2 ring-primary transition-all duration-300 ease-out"
          style={{ ...alvo, boxShadow: "0 0 0 9999px rgba(10, 12, 16, 0.6)" }}
        />
      ) : (
        <div aria-hidden className="fixed inset-0 bg-black/60 backdrop-blur-[2px]" />
      )}
      <div
        ref={balao}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-titulo"
        aria-describedby="tutorial-texto"
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === "Escape") fechar();
          else if (e.key === "ArrowRight") avancar();
          else if (e.key === "ArrowLeft") voltar();
        }}
        className={cn(
          "fixed rounded-2xl border bg-card p-5 pt-4 shadow-2xl outline-none transition-[top,left,opacity] duration-300 ease-out",
          !posicao && "opacity-0",
        )}
        style={{ width: `min(${LARGURA}px, calc(100vw - ${MARGEM * 2}px))`, top: posicao?.top ?? 0, left: posicao?.left ?? 0 }}
      >
        <button
          type="button"
          onClick={fechar}
          aria-label="Pular tutorial"
          className="absolute top-3 right-3 cursor-pointer rounded-lg p-1.5 text-muted-foreground hover:bg-subtle hover:text-foreground"
        >
          <XIcon className="size-4" />
        </button>
        <div className="flex items-start gap-3 pr-6">
          {/* eslint-disable-next-line @next/next/no-img-element -- recorte estático pequeno, sem otimização do Next */}
          <img key={passo.nico} src={urlNico(passo.nico)} alt="" className="size-20 shrink-0 object-contain" />
          <div className="min-w-0 pt-1">
            <span className="text-[11px] font-semibold tracking-widest text-primary-ink uppercase">
              {indice + 1} de {passos.length}
            </span>
            <h2 id="tutorial-titulo" className="mt-1 text-base leading-snug font-bold text-foreground">
              {passo.titulo}
            </h2>
          </div>
        </div>
        <p id="tutorial-texto" className="mt-3 text-[13px] leading-relaxed text-text-secondary">
          {passo.texto}
        </p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <div className="flex gap-1" aria-hidden>
            {passos.map((p, i) => (
              <span key={p.titulo} className={cn("h-1.5 rounded-full bg-border transition-all", i === indice ? "w-4 bg-primary" : "w-1.5")} />
            ))}
          </div>
          <div className="flex gap-2">
            {indice === 0 ? (
              <Button variant="ghost" size="sm" onClick={fechar}>
                Pular
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={voltar}>
                <ArrowLeftIcon /> Voltar
              </Button>
            )}
            <Button size="sm" onClick={avancar}>
              {ultimo ? "Começar" : indice === 0 ? "Bora!" : "Próximo"} {!ultimo && <ArrowRightIcon />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
