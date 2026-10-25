"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { InfoIcon, ShieldAlertIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useLoginSenha } from "@/features/auth/api";
import { ApiError, loginUrl } from "@/services/api/client";

const schema = z.object({
  email: z.string().trim().email("Informe um e-mail corporativo válido (ex.: nome@v4bounnacorso.com.br)."),
  senha: z.string().min(1, "Digite sua senha."),
  manter: z.boolean(),
});
type Form = z.infer<typeof schema>;

const CAMPO =
  "h-10 w-full rounded-xl border border-white/15 bg-white/5 px-3.5 text-[13px] text-white transition-all placeholder:text-white/35 focus:border-[#e5484d] focus:outline-none focus:ring-2 focus:ring-[#e5484d]/30 aria-invalid:border-rose-400";

function mensagemLogin(e: unknown): string {
  if (e instanceof ApiError && e.status === 429) return "Muitas tentativas. Aguarde alguns minutos e tente novamente.";
  if (e instanceof ApiError && e.status === 401) return e.message;
  return "Não foi possível entrar agora. Tente novamente em instantes.";
}

function Aviso({ tom, titulo, children }: { tom: "erro" | "info"; titulo: string; children: ReactNode }) {
  const erro = tom === "erro";
  return (
    <div
      role={erro ? "alert" : "status"}
      className={
        "mb-4 flex items-start gap-2.5 rounded-xl border p-3 text-xs " +
        (erro ? "border-rose-500/30 bg-rose-500/15 text-rose-200" : "border-blue-500/30 bg-blue-500/15 text-blue-200")
      }
    >
      {erro ? (
        <ShieldAlertIcon className="mt-0.5 size-4 shrink-0 text-rose-400" aria-hidden />
      ) : (
        <InfoIcon className="mt-0.5 size-4 shrink-0 text-blue-400" aria-hidden />
      )}
      <div>
        <strong className={"block font-semibold " + (erro ? "text-rose-100" : "text-blue-100")}>{titulo}</strong>
        <span className={"text-[11px] leading-relaxed " + (erro ? "text-rose-200/90" : "text-blue-200/90")}>{children}</span>
      </div>
    </div>
  );
}

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
  const router = useRouter();
  const login = useLoginSenha();
  const [esqueci, setEsqueci] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { email: "", senha: "", manter: true } });
  const erroCampo = errors.email?.message ?? errors.senha?.message;

  const entrar = handleSubmit((f) => {
    setEsqueci(false);
    login.mutate(
      { email: f.email, senha: f.senha, manter_conectado: f.manter },
      { onSuccess: () => router.replace("/") },
    );
  });
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
          SSO Ativo
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
          Entre com sua credencial corporativa ou Google Workspace para acompanhar os indicadores da carteira.
        </p>
      </div>

      {erro && !login.isError && (
        <Aviso tom="erro" titulo="Não foi possível entrar">
          {MOTIVOS[erro] ?? "Tente novamente em instantes."}
        </Aviso>
      )}
      {login.isError && (
        <Aviso tom="erro" titulo="Falha na autenticação">
          {mensagemLogin(login.error)}
        </Aviso>
      )}
      {esqueci && (
        <Aviso tom="info" titulo="Redefinição de senha">
          Peça a um administrador da V4 Bounnacorso para redefinir sua senha em Usuários. Se sua conta estiver
          vinculada ao Google, você também pode entrar com o Google Workspace e trocar a senha em Configurações.
        </Aviso>
      )}

      <a
        href={loginUrl()}
        className="flex h-11 w-full items-center justify-center gap-2.5 rounded-xl bg-white text-[13px] font-semibold text-[#14161a] shadow-md transition-colors hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e5484d]"
      >
        <LogoGoogle />
        Entrar com Google Workspace
      </a>

      <div className="my-4 flex items-center gap-3 text-[11px] text-white/45">
        <div className="h-px flex-1 bg-white/10" />
        <span>ou acesse com e-mail e senha</span>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      <form onSubmit={entrar} noValidate className="space-y-3.5" aria-label="Entrar com e-mail e senha">
        <div>
          <label htmlFor="login-email" className="mb-1.5 block text-[11px] font-medium text-white/80">
            E-mail corporativo
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            placeholder="nome@v4bounnacorso.com.br"
            aria-invalid={!!errors.email}
            aria-describedby={erroCampo ? "login-erro" : undefined}
            className={CAMPO}
            {...register("email")}
          />
        </div>
        <div>
          <label htmlFor="login-senha" className="mb-1.5 block text-[11px] font-medium text-white/80">
            Senha de acesso
          </label>
          <input
            id="login-senha"
            type="password"
            autoComplete="current-password"
            placeholder="Digite sua senha"
            aria-invalid={!!errors.senha}
            aria-describedby={erroCampo ? "login-erro" : undefined}
            className={CAMPO}
            {...register("senha")}
          />
        </div>
        {erroCampo && (
          <p id="login-erro" role="alert" className="text-[11px] text-rose-300">
            {erroCampo}
          </p>
        )}
        <div className="flex items-center justify-between gap-2 pt-0.5 text-[11px] text-white/65">
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input type="checkbox" className="size-3.5 rounded accent-[#e5484d]" {...register("manter")} />
            Manter sessão ativa
          </label>
          <button type="button" onClick={() => setEsqueci(true)} className="cursor-pointer text-[#f87171] hover:underline">
            Esqueci minha senha
          </button>
        </div>
        <button
          type="submit"
          disabled={login.isPending}
          className="flex h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-[#e5484d] text-[13px] font-semibold text-white shadow-[0_8px_24px_rgba(229,72,77,0.4)] transition-colors hover:bg-[#dc2626] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-60"
        >
          {login.isPending ? (
            <>
              <span aria-hidden className="size-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Validando credenciais…
            </>
          ) : (
            "Entrar na plataforma"
          )}
        </button>
      </form>

      <p className="mt-5 border-t border-white/10 pt-4 text-center text-[11px] leading-relaxed text-white/45">
        Acesso restrito e auditado para colaboradores autorizados da{" "}
        <strong className="font-medium text-white/70">V4 Bounnacorso</strong>. Não há cadastro público: o acesso é
        concedido por um administrador.
      </p>
    </section>
  );
}
