import { lazy, Suspense } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { pode, useAuth } from "./lib/auth";
import { PAPEL_LABEL } from "./lib/format";
import ClientesPage from "./pages/ClientesPage";
import LoginPage from "./pages/LoginPage";

// Telas com gráficos carregam sob demanda (recharts é o maior pacote).
const ClienteDetalhePage = lazy(() => import("./pages/ClienteDetalhePage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsuariosPage = lazy(() => import("./pages/UsuariosPage"));
const AuditoriaPage = lazy(() => import("./pages/AuditoriaPage"));

export default function App() {
  const { me, carregando, sair } = useAuth();
  if (carregando) return <p className="muted center">Carregando…</p>;
  if (!me) return <LoginPage />;

  return (
    <div className="layout">
      <header className="topbar">
        <span className="brand">V4 Insights</span>
        <nav>
          <NavLink to="/clientes">Clientes</NavLink>
          {pode.verUsuarios(me.papel) && <NavLink to="/usuarios">Usuários</NavLink>}
          {pode.auditoria(me.papel) && <NavLink to="/auditoria">Auditoria</NavLink>}
        </nav>
        <div className="user">
          <span>
            {me.nome} · <small>{PAPEL_LABEL[me.papel]}</small>
          </span>
          <button className="btn btn-small" onClick={sair}>
            Sair
          </button>
        </div>
      </header>
      <main className="content">
        <Suspense fallback={<p className="muted">Carregando…</p>}>
          <Routes>
            <Route path="/" element={<Navigate to="/clientes" replace />} />
            <Route path="/clientes" element={<ClientesPage />} />
            <Route path="/clientes/:id" element={<ClienteDetalhePage />} />
            <Route path="/dashboards/:id" element={<DashboardPage />} />
            {pode.verUsuarios(me.papel) && <Route path="/usuarios" element={<UsuariosPage />} />}
            {pode.auditoria(me.papel) && <Route path="/auditoria" element={<AuditoriaPage />} />}
            <Route path="*" element={<p>Página não encontrada.</p>} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
