import { loginUrl } from "../api/client";

export default function LoginPage() {
  const erro = new URLSearchParams(window.location.search).get("erro");
  return (
    <div className="login">
      <div className="card login-card">
        <h1>V4 Insights</h1>
        <p className="muted">Acesso restrito a colaboradores cadastrados.</p>
        {erro && <p className="alert alert-error">Não foi possível entrar. Fale com um administrador.</p>}
        <a className="btn btn-primary btn-block" href={loginUrl()}>
          Entrar com Google
        </a>
      </div>
    </div>
  );
}
