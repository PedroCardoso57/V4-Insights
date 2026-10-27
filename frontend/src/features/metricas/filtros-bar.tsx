"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PLATAFORMA_LABEL, PLATAFORMAS, type Plataforma } from "@/lib/format";
import type { Schemas } from "@/services/api/client";

import type { Filtros, Granularidade } from "./api";

const TODAS = "__todas__";

export function FiltrosBar({
  filtros,
  onChange,
  integracoes = [],
  campanhas = [],
}: {
  filtros: Filtros;
  onChange: (f: Filtros) => void;
  integracoes?: Schemas["IntegracaoOut"][];
  campanhas?: { id: string; nome: string }[];
}) {
  const set = (p: Partial<Filtros>) => onChange({ ...filtros, ...p });
  const contas = integracoes
    .filter((i) => !filtros.plataforma || i.plataforma === filtros.plataforma)
    .flatMap((i) => i.contas.map((c) => ({ ...c, plataforma: i.plataforma })));
  return (
    <fieldset className="flex flex-wrap items-end gap-3 rounded-xl border bg-card p-4 shadow-xs" aria-label="Filtros">
      <legend className="sr-only">Filtros</legend>
      <div className="grid gap-1">
        <Label htmlFor="f-inicio" className="text-[11px] text-muted-foreground">De</Label>
        <Input id="f-inicio" type="date" className="w-40" value={filtros.inicio} max={filtros.fim}
          onChange={(e) => e.target.value && set({ inicio: e.target.value })} />
      </div>
      <div className="grid gap-1">
        <Label htmlFor="f-fim" className="text-[11px] text-muted-foreground">Até</Label>
        <Input id="f-fim" type="date" className="w-40" value={filtros.fim} min={filtros.inicio}
          onChange={(e) => e.target.value && set({ fim: e.target.value })} />
      </div>
      <div className="grid gap-1">
        <Label className="text-[11px] text-muted-foreground" id="f-plat">Plataforma</Label>
        <Select value={filtros.plataforma || TODAS}
          onValueChange={(v) => set({ plataforma: v === TODAS ? "" : (v as Plataforma), conta_anuncio_id: "", campanha_id: "" })}>
          <SelectTrigger className="w-40" aria-labelledby="f-plat"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={TODAS}>Todas</SelectItem>
            {PLATAFORMAS.map((p) => (
              <SelectItem key={p} value={p}>{PLATAFORMA_LABEL[p]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {contas.length > 0 && (
        <div className="grid gap-1">
          <Label className="text-[11px] text-muted-foreground" id="f-conta">Conta</Label>
          <Select value={filtros.conta_anuncio_id || TODAS}
            onValueChange={(v) => set({ conta_anuncio_id: v === TODAS ? "" : v, campanha_id: "" })}>
            <SelectTrigger className="w-52" aria-labelledby="f-conta"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={TODAS}>Todas</SelectItem>
              {contas.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.nome} · {PLATAFORMA_LABEL[c.plataforma]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {campanhas.length > 0 && (
        <div className="grid gap-1">
          <Label className="text-[11px] text-muted-foreground" id="f-camp">Campanha</Label>
          <Select value={filtros.campanha_id || TODAS} onValueChange={(v) => set({ campanha_id: v === TODAS ? "" : v })}>
            <SelectTrigger className="w-56" aria-labelledby="f-camp"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={TODAS}>Todas</SelectItem>
              {campanhas.map((c) => (
                <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      <div className="grid gap-1">
        <Label className="text-[11px] text-muted-foreground" id="f-gran">Granularidade</Label>
        <Select value={filtros.granularidade} onValueChange={(v) => set({ granularidade: v as Granularidade })}>
          <SelectTrigger className="w-32" aria-labelledby="f-gran"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="dia">Diária</SelectItem>
            <SelectItem value="semana">Semanal</SelectItem>
            <SelectItem value="mes">Mensal</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Label className="h-9 text-xs font-normal text-text-secondary">
        <Checkbox checked={filtros.comparar} onCheckedChange={(v) => set({ comparar: v === true })} />
        Comparar com período anterior
      </Label>
    </fieldset>
  );
}
