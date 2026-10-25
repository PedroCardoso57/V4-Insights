"use client";

import { AlertTriangleIcon, BuildingIcon, FileTextIcon, PlugIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Consulta, Vazio } from "@/components/estado";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useClientes } from "@/features/clientes/api";
import { useIntegracoes } from "@/features/integracoes/api";
import { useMe } from "@/hooks/use-me";
import { fmtDataHora, horasDesde, PLATAFORMA_LABEL } from "@/lib/format";
import { pode } from "@/lib/permissoes";

export default function InicioPage() {
  const me = useMe().data;
  const clientes = useClientes({ status: "ativo", page_size: 12, order_by: "atualizado_em", order: "desc" });
  const integracoes = useIntegracoes();
  const [agora] = useState(() => Date.now());
  const nomes = new Map(clientes.data?.items.map((c) => [c.id, c.nome]));
  const alertas = (integracoes.data?.items ?? []).filter((i) => {
    if (i.status === "erro" || i.status === "pendente") return true;
    const h = horasDesde(i.ultima_sincronizacao_em, agora);
    return i.status === "conectada" && (h === null || h > 24);
  });

  return (
    <>
      <PageHeader titulo={`Olá, ${me?.nome.split(" ")[0] ?? ""}`} descricao="Seus clientes, alertas de sincronização e atalhos." />
      <div className="mb-6 flex flex-wrap gap-2">
        <Button asChild variant="outline"><Link href="/clientes"><BuildingIcon /> Clientes</Link></Button>
        <Button asChild variant="outline"><Link href="/relatorios"><FileTextIcon /> Relatórios</Link></Button>
        {pode.editar(me?.papel) && <Button asChild variant="outline"><Link href="/integracoes"><PlugIcon /> Integrações</Link></Button>}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Clientes atribuídos</CardTitle></CardHeader>
          <CardContent>
            <Consulta query={clientes} vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhum cliente na sua carteira">Peça a um gestor ou administrador para atribuir clientes a você.</Vazio>}>
              {(d) => (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {d.items.map((c) => (
                    <li key={c.id}>
                      <Link href={`/clientes/${c.id}`} className="block rounded-lg border p-3 hover:bg-accent">
                        <span className="font-medium">{c.nome}</span>
                        {c.nome_fantasia && <span className="block text-xs text-muted-foreground">{c.nome_fantasia}</span>}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Consulta>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Alertas de sincronização</CardTitle></CardHeader>
          <CardContent>
            {!pode.editar(me?.papel) ? (
              <p className="text-sm text-muted-foreground">Os avisos de atualização aparecem em cada dashboard.</p>
            ) : (
              <Consulta query={integracoes} vazio={() => alertas.length === 0 && <p className="text-sm text-muted-foreground">Nenhum alerta: todas as integrações estão em dia.</p>}>
                {() => (
                  <ul className="grid gap-2">
                    {alertas.map((i) => (
                      <li key={i.id} className="flex items-start gap-2 text-sm">
                        <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
                        <span>
                          <Link className="font-medium underline" href={`/integracoes?cliente_id=${i.cliente_id}`}>
                            {nomes.get(i.cliente_id) ?? "Cliente"} · {PLATAFORMA_LABEL[i.plataforma]}
                          </Link>{" "}
                          <Badge variant={i.status === "erro" ? "destructive" : "warning"}>
                            {i.status === "erro" ? "requer reconexão" : i.status === "pendente" ? "aguardando contas" : "desatualizada"}
                          </Badge>
                          <span className="block text-xs text-muted-foreground">Última sincronização: {fmtDataHora(i.ultima_sincronizacao_em)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Consulta>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
