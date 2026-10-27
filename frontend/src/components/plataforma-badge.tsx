import { PLATAFORMA_LABEL, type Plataforma } from "@/lib/format";
import { cn } from "@/lib/utils";

const TOM: Record<Plataforma, { fundo: string; ponto: string }> = {
  meta_ads: { fundo: "bg-info-soft text-info", ponto: "bg-info" },
  google_ads: { fundo: "bg-primary-soft text-primary-ink", ponto: "bg-primary" },
  linkedin_ads: { fundo: "bg-success-soft text-success", ponto: "bg-success" },
  tiktok_ads: { fundo: "bg-secondary text-foreground", ponto: "bg-foreground" },
};

/** Selo da plataforma de mídia (Meta Ads em azul, Google Ads em vermelho, como no gráfico; LinkedIn em verde, TikTok neutro). */
export function PlataformaBadge({ plataforma, className }: { plataforma: Plataforma; className?: string }) {
  const t = TOM[plataforma];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium whitespace-nowrap", t.fundo, className)}>
      <span aria-hidden className={cn("size-1.5 rounded-full", t.ponto)} />
      {PLATAFORMA_LABEL[plataforma]}
    </span>
  );
}
