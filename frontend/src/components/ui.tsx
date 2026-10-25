import { useEffect, useRef, type ReactNode } from "react";

export function Modal({
  titulo,
  aberto,
  onFechar,
  children,
  rodape,
}: {
  titulo: string;
  aberto: boolean;
  onFechar: () => void;
  children: ReactNode;
  rodape?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (aberto && !d.open) d.showModal?.();
    if (!aberto && d.open) d.close?.();
  }, [aberto]);
  if (!aberto) return null;
  return (
    <dialog ref={ref} className="modal" onCancel={onFechar} aria-label={titulo} open>
      <header className="modal-header">
        <h2>{titulo}</h2>
        <button className="btn-icon" onClick={onFechar} aria-label="Fechar">
          ×
        </button>
      </header>
      <div className="modal-body">{children}</div>
      {rodape && <footer className="modal-footer">{rodape}</footer>}
    </dialog>
  );
}

export function Confirmar({
  aberto,
  titulo,
  mensagem,
  acao,
  perigo,
  onConfirmar,
  onCancelar,
}: {
  aberto: boolean;
  titulo: string;
  mensagem: ReactNode;
  acao: string;
  perigo?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
}) {
  return (
    <Modal
      titulo={titulo}
      aberto={aberto}
      onFechar={onCancelar}
      rodape={
        <>
          <button className="btn" onClick={onCancelar}>
            Cancelar
          </button>
          <button className={perigo ? "btn btn-danger" : "btn btn-primary"} onClick={onConfirmar}>
            {acao}
          </button>
        </>
      }
    >
      <p>{mensagem}</p>
    </Modal>
  );
}

export function Estado({
  carregando,
  erro,
  vazio,
  mensagemVazia,
  children,
}: {
  carregando?: boolean;
  erro?: string | null;
  vazio?: boolean;
  mensagemVazia?: ReactNode;
  children: ReactNode;
}) {
  if (carregando) return <p className="muted">Carregando…</p>;
  if (erro) return <p className="alert alert-error">{erro}</p>;
  if (vazio) return <div className="empty">{mensagemVazia ?? "Nenhum registro."}</div>;
  return <>{children}</>;
}

export function Badge({ children, tom }: { children: ReactNode; tom?: string }) {
  return <span className={`badge ${tom ? `badge-${tom}` : ""}`}>{children}</span>;
}

export function Paginacao({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
}) {
  const paginas = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav className="pagination" aria-label="Paginação">
      <button className="btn" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Anterior
      </button>
      <span>
        Página {page} de {paginas} · {total} registros
      </span>
      <button className="btn" disabled={page >= paginas} onClick={() => onPage(page + 1)}>
        Próxima
      </button>
    </nav>
  );
}
