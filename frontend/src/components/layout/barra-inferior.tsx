"use client";

import { MenuIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { itemAtivo, useItensNav } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";

const NA_BARRA = ["Visão geral", "Clientes", "Dashboards", "Relatórios"];
const CURTO: Record<string, string> = { "Visão geral": "Início" };

/** Navegação fixa no rodapé do celular: as quatro áreas mais usadas e o "Mais", que abre o menu completo. */
export function BarraInferior({ onMais, menuAberto }: { onMais: () => void; menuAberto: boolean }) {
  const path = usePathname();
  const itens = useItensNav();
  const naBarra = itens.filter((i) => NA_BARRA.includes(i.label));
  const resto = itens.filter((i) => !NA_BARRA.includes(i.label));
  const restoAtivo = resto.some((i) => itemAtivo(i.label, i.href, path));
  const alertas = resto.reduce((n, i) => n + (i.contador ?? 0), 0);
  const classe = (ativo: boolean) =>
    cn(
      "relative flex flex-1 flex-col items-center justify-center gap-1 pt-2 pb-1.5 text-[10.5px] font-medium text-muted-foreground transition-colors active:bg-subtle",
      ativo && "font-semibold text-primary-ink",
    );
  const marcador = (ativo: boolean) =>
    ativo && <span aria-hidden className="absolute top-0 left-1/2 h-[3px] w-8 -translate-x-1/2 rounded-b-full bg-primary" />;

  return (
    <nav
      aria-label="Navegação rápida"
      className="fixed inset-x-0 bottom-0 z-30 border-t bg-card/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_16px_-8px_rgba(16,24,40,0.12)] backdrop-blur-md lg:hidden"
    >
      <ul className="mx-auto flex max-w-xl">
        {naBarra.map(({ href, label, icon: Icon }) => {
          const ativo = itemAtivo(label, href, path);
          return (
            <li key={label} className="flex flex-1">
              <Link href={href} data-tour={`nav:${label}`} aria-current={ativo ? "page" : undefined} className={classe(ativo)}>
                {marcador(ativo)}
                <Icon className="size-5" aria-hidden />
                {CURTO[label] ?? label}
              </Link>
            </li>
          );
        })}
        <li className="flex flex-1">
          <button type="button" onClick={onMais} aria-expanded={menuAberto} className={cn(classe(restoAtivo), "cursor-pointer")}>
            {marcador(restoAtivo)}
            <span className="relative">
              <MenuIcon className="size-5" aria-hidden />
              {alertas > 0 && (
                <span aria-hidden className="absolute -top-1 -right-2 rounded-full bg-primary px-1 text-[9px] leading-[14px] font-bold text-white">
                  {alertas}
                </span>
              )}
            </span>
            Mais
            {alertas > 0 && <span className="sr-only">({alertas} {alertas === 1 ? "alerta" : "alertas"})</span>}
          </button>
        </li>
      </ul>
    </nav>
  );
}
