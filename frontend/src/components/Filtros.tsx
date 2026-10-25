import type { Filtros, Integracao } from "../api/types";
import { isoHoje, PLATAFORMA_LABEL } from "../lib/format";

export const filtrosPadrao = (): Filtros => ({
  inicio: isoHoje(-29),
  fim: isoHoje(0),
  plataforma: "",
  conta_anuncio_id: "",
  campanha_id: "",
  granularidade: "dia",
  comparar: true,
});

export function filtrosQuery(f: Filtros) {
  return {
    inicio: f.inicio,
    fim: f.fim,
    plataforma: f.plataforma,
    conta_anuncio_id: f.conta_anuncio_id,
    campanha_id: f.campanha_id,
  };
}

export default function FiltrosBar({
  filtros,
  onChange,
  integracoes,
  campanhas,
}: {
  filtros: Filtros;
  onChange: (f: Filtros) => void;
  integracoes: Integracao[];
  campanhas: { id: string; nome: string }[];
}) {
  const set = (patch: Partial<Filtros>) => onChange({ ...filtros, ...patch });
  const contas = integracoes
    .filter((i) => !filtros.plataforma || i.plataforma === filtros.plataforma)
    .flatMap((i) => i.contas.map((c) => ({ ...c, plataforma: i.plataforma })));

  return (
    <div className="toolbar filtros" aria-label="Filtros">
      <label>
        De
        <input
          type="date"
          value={filtros.inicio}
          max={filtros.fim}
          onChange={(e) => e.target.value && set({ inicio: e.target.value })}
        />
      </label>
      <label>
        Até
        <input
          type="date"
          value={filtros.fim}
          min={filtros.inicio}
          onChange={(e) => e.target.value && set({ fim: e.target.value })}
        />
      </label>
      <label>
        Plataforma
        <select
          value={filtros.plataforma}
          onChange={(e) =>
            set({
              plataforma: e.target.value as Filtros["plataforma"],
              conta_anuncio_id: "",
              campanha_id: "",
            })
          }
        >
          <option value="">Todas</option>
          <option value="meta">{PLATAFORMA_LABEL.meta}</option>
          <option value="google_ads">{PLATAFORMA_LABEL.google_ads}</option>
        </select>
      </label>
      {contas.length > 0 && (
        <label>
          Conta
          <select
            value={filtros.conta_anuncio_id}
            onChange={(e) => set({ conta_anuncio_id: e.target.value, campanha_id: "" })}
          >
            <option value="">Todas</option>
            {contas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome} ({PLATAFORMA_LABEL[c.plataforma]})
              </option>
            ))}
          </select>
        </label>
      )}
      {campanhas.length > 0 && (
        <label>
          Campanha
          <select value={filtros.campanha_id} onChange={(e) => set({ campanha_id: e.target.value })}>
            <option value="">Todas</option>
            {campanhas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        Granularidade
        <select
          value={filtros.granularidade}
          onChange={(e) => set({ granularidade: e.target.value as Filtros["granularidade"] })}
        >
          <option value="dia">Diária</option>
          <option value="semana">Semanal</option>
          <option value="mes">Mensal</option>
        </select>
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={filtros.comparar}
          onChange={(e) => set({ comparar: e.target.checked })}
        />
        Comparar com período anterior
      </label>
    </div>
  );
}
