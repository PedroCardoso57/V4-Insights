"use client";

import { ShieldAlertIcon } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { loginUrl } from "@/services/api/client";

const MOTIVOS: Record<string, string> = {
  acesso_negado: "Sua conta Google não está autorizada. Peça a um administrador para cadastrar seu e-mail.",
  token_invalido: "Não foi possível validar sua identidade no Google. Tente novamente.",
  state_invalido: "O login expirou ou foi reaproveitado. Inicie novamente.",
  autorizacao_cancelada: "O login foi cancelado na tela do Google.",
};

function LogoGoogle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z" />
      <path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z" />
      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z" />
    </svg>
  );
}

export function LoginCard() {
  const erro = useSearchParams().get("erro");
  return (
    <section
      aria-labelledby="titulo-login"
      className="relative z-10 w-full max-w-[430px] rounded-2xl border border-white/15 bg-[#111318]/90 p-7 text-white shadow-[0_32px_90px_rgba(0,0,0,0.75)] backdrop-blur-xl sm:p-8"
    >
      <div className="mb-6 flex items-center justify-between gap-3 border-b border-white/10 pb-5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex size-10 items-center justify-center rounded-xl bg-[#e5484d] text-base font-extrabold tracking-tighter shadow-[0_0_24px_rgba(229,72,77,0.55)]"
          >
            V4
          </span>
          <div>
            <strong className="block text-base font-bold tracking-tight">V4 Insights</strong>
            <span className="mt-0.5 block text-xs text-white/60">Unidade V4 Bounnacorso</span>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-400">
          <span aria-hidden className="size-1.5 animate-pulse rounded-full bg-emerald-400 motion-reduce:animate-none" />
          SSO Google
        </span>
      </div>

      <div className="mb-6">
        <span className="text-[11px] font-semibold tracking-widest text-[#f87171] uppercase">
          Inteligência de Mídia &amp; Performance
        </span>
        <h1 id="titulo-login" className="mt-1 text-2xl font-bold tracking-tight">
          Acesse sua conta
        </h1>
        <p className="mt-1 text-xs leading-relaxed text-white/65">
          Entre com sua conta Google Workspace corporativa para acompanhar os indicadores da carteira.
        </p>
      </div>

      {erro && (
        <div role="alert" className="mb-4 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/15 p-3 text-xs text-rose-200">
          <ShieldAlertIcon className="mt-0.5 size-4 shrink-0 text-rose-400" aria-hidden />
          <div>
            <strong className="block font-semibold text-rose-100">Não foi possível entrar</strong>
            <span className="text-[11px] leading-relaxed text-rose-200/90">{MOTIVOS[erro] ?? "Tente novamente em instantes."}</span>
          </div>
        </div>
      )}

      <a
        href={loginUrl()}
        className="flex h-11 w-full items-center justify-center gap-2.5 rounded-xl bg-white text-[13px] font-semibold text-[#14161a] shadow-md transition-colors hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e5484d]"
      >
        <LogoGoogle />
        Entrar com Google Workspace
      </a>

      <p className="mt-5 border-t border-white/10 pt-4 text-center text-[11px] leading-relaxed text-white/45">
        Acesso restrito e auditado para colaboradores autorizados da{" "}
        <strong className="font-medium text-white/70">V4 Bounnacorso</strong>. Não há cadastro público: o acesso é
        concedido por convite.
      </p>
    </section>
  );
}
