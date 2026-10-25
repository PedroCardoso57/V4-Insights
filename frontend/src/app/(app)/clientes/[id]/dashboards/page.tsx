"use client";

import { useParams } from "next/navigation";

import { Consulta } from "@/components/estado";
import { PageHeader } from "@/components/page-header";
import { useCliente } from "@/features/clientes/api";
import { DashboardsCliente } from "@/features/dashboards/dashboards-cliente";

export default function DashboardsPage() {
  const { id } = useParams<{ id: string }>();
  const q = useCliente(id);
  return (
    <Consulta query={q}>
      {(c) => (
        <>
          <PageHeader titulo={`Dashboards · ${c.nome}`} descricao="Os filtros se aplicam a todos os cards, gráficos e tabelas do painel." />
          <DashboardsCliente clienteId={c.id} />
        </>
      )}
    </Consulta>
  );
}
