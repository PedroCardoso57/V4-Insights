"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Consulta, mensagemDeErro, Vazio } from "@/components/estado";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PLATAFORMA_LABEL, type Plataforma } from "@/lib/format";

import { useContasDisponiveis, useSelecionarContas, type Integracao } from "./api";

/** Exemplos de tipos de conversão aceitos no mapeamento de cada plataforma. */
const PLACEHOLDER_CONVERSAO: Record<Plataforma, string> = {
  meta_ads: "ex.: purchase, lead",
  google_ads: "conversions",
  linkedin_ads: "external_website_conversions, one_click_leads",
  tiktok_ads: "conversion, complete_payment",
};

export function SelecionarContasDialog({ integracao, onClose }: { integracao: Integracao | null; onClose: () => void }) {
  // `key` reinicia o estado do formulário a cada integração aberta.
  return integracao ? <Conteudo key={integracao.id} integracao={integracao} onClose={onClose} /> : null;
}

function Conteudo({ integracao, onClose }: { integracao: Integracao; onClose: () => void }) {
  const q = useContasDisponiveis(integracao.id);
  const salvar = useSelecionarContas();
  const [marcadas, setMarcadas] = useState<Set<string>>(
    () => new Set(integracao.contas.filter((c) => c.ativa).map((c) => c.conta_externa_id)),
  );
  const [acoes, setAcoes] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      integracao.contas.map((c) => [c.conta_externa_id, ((c.mapeamento_conversoes as { action_types?: string[] }).action_types ?? []).join(", ")]),
    ),
  );
  const [dias, setDias] = useState(90);
  const existentes = new Map(integracao.contas.map((c) => [c.conta_externa_id, c]));

  const enviar = () => {
    const contas = [...marcadas].map((id) => {
      const tipos = (acoes[id] ?? "").split(",").map((s) => s.trim()).filter(Boolean);
      const atual = ((existentes.get(id)?.mapeamento_conversoes as { action_types?: string[] })?.action_types ?? []).join(",");
      const mudou = tipos.join(",") !== atual;
      return {
        conta_externa_id: id,
        carga_historica_dias: existentes.has(id) ? null : dias,
        // Conta nova sem preenchimento usa o padrão do provedor.
        mapeamento_conversoes: mudou && (tipos.length || existentes.has(id)) ? { action_types: tipos } : null,
      };
    });
    salvar.mutate(
      { id: integracao.id, body: { contas } },
      {
        onSuccess: () => {
          toast.success("Contas salvas. A carga histórica foi agendada.");
          onClose();
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    );
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Contas — {PLATAFORMA_LABEL[integracao.plataforma]}</DialogTitle>
          <DialogDescription>Somente contas autorizadas para este acesso são listadas.</DialogDescription>
        </DialogHeader>
        <Consulta query={q} vazio={(d) => d.items.length === 0 && <Vazio titulo="Nenhuma conta autorizada encontrada" />}>
          {(d) => (
            <div className="grid gap-3">
              <div className="grid max-w-60 gap-1.5">
                <Label htmlFor="dias">Carga histórica para contas novas (dias)</Label>
                <Input id="dias" type="number" min={1} max={1095} value={dias}
                  onChange={(e) => setDias(Math.min(1095, Math.max(1, Number(e.target.value) || 1)))} />
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"><span className="sr-only">Selecionar</span></TableHead>
                    <TableHead>Conta</TableHead>
                    <TableHead>Moeda</TableHead>
                    <TableHead>Ações de conversão</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.items.map((c) => (
                    <TableRow key={c.conta_externa_id}>
                      <TableCell>
                        <Checkbox
                          aria-label={`Selecionar ${c.nome}`}
                          checked={marcadas.has(c.conta_externa_id)}
                          onCheckedChange={(v) => {
                            const n = new Set(marcadas);
                            if (v === true) n.add(c.conta_externa_id);
                            else n.delete(c.conta_externa_id);
                            setMarcadas(n);
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        {c.nome} <span className="text-xs text-muted-foreground">{c.conta_externa_id}</span>
                      </TableCell>
                      <TableCell>{c.moeda ?? "—"}</TableCell>
                      <TableCell>
                        <Input
                          aria-label={`Ações de conversão de ${c.nome}`}
                          placeholder={PLACEHOLDER_CONVERSAO[integracao.plataforma]}
                          value={acoes[c.conta_externa_id] ?? ""}
                          onChange={(e) => setAcoes({ ...acoes, [c.conta_externa_id]: e.target.value })}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Consulta>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={enviar} disabled={!marcadas.size || salvar.isPending}>Salvar seleção</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
