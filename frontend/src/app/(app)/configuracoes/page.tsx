"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2Icon, MoonIcon, SunIcon, XCircleIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { SenhaCard } from "@/features/auth/senha-card";
import { ChavesCard } from "@/features/configuracoes/chaves-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/hooks/use-me";
import { PAPEL_LABEL } from "@/lib/format";
import { pode } from "@/lib/permissoes";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { useTema } from "@/hooks/use-tema";
import { cn } from "@/lib/utils";
import { parsePreferencias, PREFERENCIAS_KEY, type Preferencias } from "@/lib/preferencias";
import { API_BASE } from "@/services/api/client";

interface Ready {
  status: string;
  checks: Record<string, string>;
}

export default function ConfiguracoesPage() {
  const me = useMe().data;
  const [tema, setTema] = useTema();
  const [salvo, salvar] = useLocalStorage(PREFERENCIAS_KEY);
  const [rascunho, setPref] = useState<Preferencias | null>(null);
  const pref = rascunho ?? parsePreferencias(salvo);
  const saude = useQuery<Ready>({
    queryKey: ["health"],
    queryFn: async () => (await fetch(`${API_BASE}/health/ready`)).json() as Promise<Ready>,
    refetchInterval: 30_000,
  });

  return (
    <>
      <PageHeader titulo="Configurações" descricao="Preferências deste navegador, status operacional e chaves das plataformas." />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-col items-start">
            <CardTitle>Aparência</CardTitle>
            <CardDescription>Tema da interface neste navegador.</CardDescription>
          </CardHeader>
          <CardContent>
            <div role="radiogroup" aria-label="Tema" className="grid max-w-md grid-cols-2 gap-3">
              {([
                { id: "claro", label: "Claro", icon: SunIcon },
                { id: "escuro", label: "Escuro", icon: MoonIcon },
              ] as const).map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  role="radio"
                  aria-checked={tema === id}
                  onClick={() => setTema(id)}
                  className={cn(
                    "flex cursor-pointer items-center gap-2.5 rounded-xl border p-3 text-left text-[13px] font-medium transition-colors hover:bg-subtle",
                    tema === id && "border-primary bg-primary-soft text-primary-ink hover:bg-primary-soft",
                  )}
                >
                  <Icon className="size-4" aria-hidden /> {label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-col items-start">
            <CardTitle>Preferências</CardTitle>
            <CardDescription>Usadas como padrão ao abrir os dashboards.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-1.5">
              <Label id="p-periodo">Período padrão</Label>
              <Select value={String(pref.periodoDias)} onValueChange={(v) => setPref({ ...pref, periodoDias: Number(v) as Preferencias["periodoDias"] })}>
                <SelectTrigger aria-labelledby="p-periodo" className="w-48"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Últimos 7 dias</SelectItem>
                  <SelectItem value="30">Últimos 30 dias</SelectItem>
                  <SelectItem value="90">Últimos 90 dias</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label id="p-gran">Granularidade padrão</Label>
              <Select value={pref.granularidade} onValueChange={(v) => setPref({ ...pref, granularidade: v as Preferencias["granularidade"] })}>
                <SelectTrigger aria-labelledby="p-gran" className="w-48"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="dia">Diária</SelectItem>
                  <SelectItem value="semana">Semanal</SelectItem>
                  <SelectItem value="mes">Mensal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Label className="font-normal">
              <Checkbox checked={pref.comparar} onCheckedChange={(v) => setPref({ ...pref, comparar: v === true })} />
              Comparar com o período anterior
            </Label>
            <div>
              <Button onClick={() => { salvar(JSON.stringify(pref)); setPref(null); toast.success("Preferências salvas neste navegador."); }}>Salvar preferências</Button>
            </div>
          </CardContent>
        </Card>
        <SenhaCard />
        <Card>
          <CardHeader className="flex-col items-start">
            <CardTitle>Status operacional</CardTitle>
            <CardDescription>Disponibilidade dos serviços da plataforma.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            {saude.isPending ? (
              <Skeleton className="h-16 rounded-xl" />
            ) : saude.isError || !saude.data ? (
              <p className="flex items-center gap-2 text-destructive"><XCircleIcon className="size-4" /> API indisponível</p>
            ) : (
              <ul className="grid gap-2">
                {Object.entries(saude.data.checks).map(([k, v]) => (
                  <li key={k} className="flex items-center gap-2">
                    {v === "ok" ? <CheckCircle2Icon className="size-4 text-success" /> : <XCircleIcon className="size-4 text-destructive" />}
                    {k === "database" ? "Banco de dados" : k === "redis" ? "Fila de processamento" : k}: {v === "ok" ? "operacional" : "indisponível"}
                  </li>
                ))}
              </ul>
            )}
            {me && (
              <p className="text-muted-foreground">
                Sessão: {me.email} · perfil {PAPEL_LABEL[me.papel]}
              </p>
            )}
          </CardContent>
        </Card>
        {pode.gerirChaves(me?.papel) && <ChavesCard />}
      </div>
    </>
  );
}
