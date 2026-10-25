"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/services/api/client";

export type Dashboard = Schemas["DashboardOut"];
export type WidgetIn = Schemas["WidgetIn"];

export function useDashboards(clienteId: string) {
  return useQuery({
    queryKey: ["dashboards", clienteId],
    queryFn: () => unwrap(api.GET("/api/v1/dashboards", { params: { query: { cliente_id: clienteId, page_size: 100 } } })),
  });
}

export function useCriarDashboard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ clienteId, nome, widgets }: { clienteId: string; nome: string; widgets: WidgetIn[] }) => {
      const d = await unwrap(api.POST("/api/v1/dashboards", { body: { cliente_id: clienteId, nome } }));
      return unwrap(api.PATCH("/api/v1/dashboards/{dashboard_id}", { params: { path: { dashboard_id: d.id } }, body: { widgets } }));
    },
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: ["dashboards", v.clienteId] }),
  });
}

export function useSalvarDashboard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Schemas["DashboardUpdate"] }) =>
      unwrap(api.PATCH("/api/v1/dashboards/{dashboard_id}", { params: { path: { dashboard_id: id } }, body })),
    onSuccess: (d) => qc.invalidateQueries({ queryKey: ["dashboards", d.cliente_id] }),
  });
}

export function useExcluirDashboard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (d: Dashboard) => unwrap(api.DELETE("/api/v1/dashboards/{dashboard_id}", { params: { path: { dashboard_id: d.id } } })),
    onSuccess: (_r, d) => qc.invalidateQueries({ queryKey: ["dashboards", d.cliente_id] }),
  });
}
