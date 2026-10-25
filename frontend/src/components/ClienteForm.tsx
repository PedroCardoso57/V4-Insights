import { useState } from "react";
import { api } from "../api/client";
import type { Cliente } from "../api/types";

export default function ClienteForm({
  cliente,
  onSalvo,
}: {
  cliente?: Cliente;
  onSalvo: (c: Cliente) => void;
}) {
  const [nome, setNome] = useState(cliente?.nome ?? "");
  const [fantasia, setFantasia] = useState(cliente?.nome_fantasia ?? "");
  const [documento, setDocumento] = useState(cliente?.documento ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const validar = (): string | null => {
    if (nome.trim().length < 2) return "Informe o nome (mínimo 2 caracteres).";
    const dig = documento.replace(/\D/g, "");
    if (dig && dig.length !== 11 && dig.length !== 14) return "Documento deve ser CPF ou CNPJ.";
    return null;
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    const v = validar();
    if (v) return setErro(v);
    setSalvando(true);
    setErro(null);
    const body = { nome, nome_fantasia: fantasia || null, documento: documento || null };
    try {
      const c = cliente
        ? await api<Cliente>(`/clientes/${cliente.id}`, { method: "PATCH", body })
        : await api<Cliente>("/clientes", { method: "POST", body });
      onSalvo(c);
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form className="form" onSubmit={salvar} noValidate>
      <label>
        Nome *
        <input value={nome} maxLength={160} required onChange={(e) => setNome(e.target.value)} />
      </label>
      <label>
        Nome fantasia
        <input value={fantasia} maxLength={160} onChange={(e) => setFantasia(e.target.value)} />
      </label>
      <label>
        CPF/CNPJ
        <input value={documento} maxLength={20} onChange={(e) => setDocumento(e.target.value)} />
      </label>
      {erro && <p className="alert alert-error">{erro}</p>}
      <button className="btn btn-primary" type="submit" disabled={salvando}>
        {salvando ? "Salvando…" : "Salvar"}
      </button>
    </form>
  );
}
