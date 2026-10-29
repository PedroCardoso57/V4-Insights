"use client";

import { useEffect, useRef } from "react";

/**
 * Nico andando de verdade: a arte do usuário separada em peças (cubo, tênis, luva) e
 * montada num boneco articulado em SVG. Pernas e braços são traços de "borracha" que
 * ligam o corpo às peças, e um ciclo de caminhada move tudo a cada quadro.
 *
 * Ele entra pela esquerda até o centro e continua andando ali, com o chão correndo
 * por baixo na mesma velocidade dos passos (o pé de apoio não escorrega).
 * Coordenadas em unidades da arte original (quadro de 340×330).
 */

const LARGURA = 578; // palco, em unidades da arte (proporção do palco do modal)
const ALTURA = 330;
const CHAO = 318;
const BASE_Y = CHAO - 316; // os tênis da arte terminam em y≈316
const CENTRO_X = (LARGURA - 340) / 2;

const CICLO_S = 0.5; // dois passos
const VELOCIDADE = 340; // unidades por segundo
const PASSO = (VELOCIDADE * CICLO_S) / 2; // quanto o pé anda em meio ciclo
const ALTURA_PASSO = 26;

const QUADRIL = { e: [152, 205], d: [226, 205] } as const;
const OMBRO = { e: [104, 140], d: [288, 150] } as const;
const PIVO = [192, 200] as const;

// Onde cada peça fica parada e o ponto em que o traço da perna/braço encaixa nela.
const TENIS = {
  e: { x: 84, y: 240, w: 87, h: 76, encaixe: [63, 6] },
  d: { x: 207, y: 247, w: 93, h: 69, encaixe: [28, 7] },
} as const;
const LUVA = { w: 53, h: 63 };
const MAO = { e: [74, 196], d: [306, 196] } as const; // ponto do punho, parado

type Ponto = readonly [number, number];
type Refs = Record<string, SVGElement | null>;

const girar = ([x, y]: Ponto, graus: number, [cx, cy]: Ponto): [number, number] => {
  const r = (graus * Math.PI) / 180;
  const dx = x - cx;
  const dy = y - cy;
  return [cx + dx * Math.cos(r) - dy * Math.sin(r), cy + dx * Math.sin(r) + dy * Math.cos(r)];
};

/** Posição do pé (deslocamento x, altura) numa fase de 0 a 1: metade apoiado, metade no ar. */
function pe(fase: number): [number, number, number] {
  if (fase < 0.5) return [PASSO / 2 - PASSO * (fase / 0.5), 0, 0];
  const u = (fase - 0.5) / 0.5;
  const suave = u * u * (3 - 2 * u);
  return [-PASSO / 2 + PASSO * suave, ALTURA_PASSO * Math.sin(Math.PI * u), -14 * Math.sin(Math.PI * u)];
}

function perna(q: Ponto, t: Ponto) {
  const meio = (t[1] - q[1]) * 0.5;
  return `M${q[0]} ${q[1]} C${q[0]} ${q[1] + meio} ${t[0]} ${t[1] - meio} ${t[0]} ${t[1]}`;
}

function braco(o: Ponto, m: Ponto, lado: 1 | -1) {
  const cx = (o[0] + m[0]) / 2 + 14 * lado;
  const cy = (o[1] + m[1]) / 2 + 6;
  return `M${o[0]} ${o[1]} Q${cx} ${cy} ${m[0]} ${m[1]}`;
}

function desenhar(refs: Refs, t: number, entradaS: number) {
  const ciclo = (t / CICLO_S) % 1;
  // Entrando: o corpo anda; depois, para no centro e o chão passa a correr.
  const andou = Math.min(t, entradaS) * VELOCIDADE;
  const x = CENTRO_X - entradaS * VELOCIDADE + andou;
  const rolagem = Math.max(0, t - entradaS) * VELOCIDADE;

  const passo = (ciclo * 2) % 1;
  const sobe = -9 * Math.sin(Math.PI * passo);
  const inclina = 4 + 1.5 * Math.sin(2 * Math.PI * ciclo);
  const corpo = (p: Ponto): [number, number] => {
    const [gx, gy] = girar(p, inclina, PIVO);
    return [gx, gy + sobe];
  };

  refs.mundo?.setAttribute("transform", `translate(${x} ${BASE_Y})`);
  refs.cubo?.setAttribute("transform", `translate(0 ${sobe}) rotate(${inclina} ${PIVO[0]} ${PIVO[1]})`);
  refs.chao?.setAttribute("transform", `translate(${-(rolagem % 60)} 0)`);
  refs.sombra?.setAttribute("rx", String(92 + sobe * 1.2));

  for (const [lado, desloc] of [["e", 0], ["d", 0.5]] as const) {
    const [dx, alt, rot] = pe((ciclo + desloc) % 1);
    const tenis = TENIS[lado];
    const ancora: Ponto = [tenis.x + tenis.encaixe[0] + dx, tenis.y + tenis.encaixe[1] - alt];
    refs[`tenis-${lado}`]?.setAttribute(
      "transform",
      `translate(${dx} ${-alt}) rotate(${rot} ${tenis.x + tenis.encaixe[0]} ${tenis.y + tenis.encaixe[1]})`,
    );
    const d = perna(corpo(QUADRIL[lado]), ancora);
    refs[`perna-${lado}`]?.setAttribute("d", d);
    refs[`perna-brilho-${lado}`]?.setAttribute("d", d);

    // Braço do mesmo lado balança ao contrário da perna.
    const mao: Ponto = [MAO[lado][0] - dx * 0.38, MAO[lado][1] - Math.abs(dx) * 0.08 + sobe * 0.6];
    const sinal = lado === "e" ? -1 : 1;
    const db = braco(corpo(OMBRO[lado]), mao, sinal);
    refs[`braco-${lado}`]?.setAttribute("d", db);
    refs[`braco-brilho-${lado}`]?.setAttribute("d", db);
    const giro = -dx * 0.25 * sinal;
    const espelho = lado === "e" ? ` translate(${2 * mao[0]} 0) scale(-1 1)` : "";
    refs[`luva-${lado}`]?.setAttribute(
      "transform",
      `rotate(${giro} ${mao[0]} ${mao[1]})${espelho} translate(${mao[0] - 33} ${mao[1] - 6})`,
    );
  }
}

export function NicoAndando({ entradaMs = 1300, className }: { entradaMs?: number; className?: string }) {
  const svg = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const refs: Refs = {};
    svg.current?.querySelectorAll<SVGElement>("[data-parte]").forEach((el) => (refs[el.dataset.parte!] = el));
    const entradaS = entradaMs / 1000;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      desenhar(refs, entradaS, entradaS);
      return;
    }
    let id = 0;
    let inicio: number | null = null;
    const quadro = (agora: number) => {
      inicio ??= agora;
      desenhar(refs, (agora - inicio) / 1000, entradaS);
      id = requestAnimationFrame(quadro);
    };
    id = requestAnimationFrame(quadro);
    return () => cancelAnimationFrame(id);
  }, [entradaMs]);

  const traco = (nome: string, largura: number) => (
    <>
      <path data-parte={nome} fill="none" stroke="#141114" strokeWidth={largura} strokeLinecap="round" />
      <path
        data-parte={nome.replace("-", "-brilho-")}
        fill="none"
        stroke="rgba(255,255,255,0.16)"
        strokeWidth={largura * 0.22}
        strokeLinecap="round"
        transform={`translate(${-largura * 0.22} ${-largura * 0.1})`}
      />
    </>
  );

  return (
    <svg ref={svg} viewBox={`0 0 ${LARGURA} ${ALTURA}`} className={className} role="img" aria-label="Nico andando">
      <g data-parte={"chao"} opacity={0.35}>
        {Array.from({ length: 12 }, (_, i) => (
          <rect key={i} x={i * 60} y={CHAO + 6} width={26} height={3} rx={1.5} fill="#ff2a35" />
        ))}
      </g>
      <g data-parte={"mundo"}>
        <ellipse data-parte={"sombra"} cx={192} cy={CHAO - BASE_Y - 2} rx={92} ry={9} fill="black" opacity={0.45} />
        {traco("braco-d", 18)}
        {traco("perna-e", 24)}
        {traco("perna-d", 24)}
        <image data-parte={"tenis-e"} href="/mascote/nico/tenis-e.webp" x={TENIS.e.x} y={TENIS.e.y} width={TENIS.e.w} height={TENIS.e.h} />
        <image data-parte={"tenis-d"} href="/mascote/nico/tenis-d.webp" x={TENIS.d.x} y={TENIS.d.y} width={TENIS.d.w} height={TENIS.d.h} />
        {traco("braco-e", 18)}
        <image data-parte={"cubo"} href="/mascote/nico/cubo.webp" x={88} y={22} width={209} height={192} />
        <image data-parte={"luva-d"} href="/mascote/nico/luva.webp" width={LUVA.w} height={LUVA.h} />
        <image data-parte={"luva-e"} href="/mascote/nico/luva.webp" width={LUVA.w} height={LUVA.h} />
      </g>
    </svg>
  );
}
