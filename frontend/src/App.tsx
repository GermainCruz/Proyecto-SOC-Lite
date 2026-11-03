import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { AlertsPage } from "./pages/Alerts";
import { AlertDetailPage } from "./pages/AlertDetail";
import { IncidentsPage } from "./pages/Incidents";
import { ReportsPage } from "./pages/Reports";
import { UsersPage } from "./pages/Users";
import { AuditPage } from "./pages/Audit";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Verificando sesión…" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth();
  if (!can(permission)) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
        Su rol no tiene el permiso <span className="font-mono">{permission}</span> requerido para este módulo.
      </div>
    );
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            >
              <Route
                index
                element={
                  <RequirePermission permission="dashboard:read">
                    <DashboardPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/alertas"
                element={
                  <RequirePermission permission="alerts:read">
                    <AlertsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/alertas/:id"
                element={
                  <RequirePermission permission="alerts:read">
                    <AlertDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/incidentes"
                element={
                  <RequirePermission permission="incidents:read">
                    <IncidentsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/reportes"
                element={
                  <RequirePermission permission="reports:read">
                    <ReportsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/usuarios"
                element={
                  <RequirePermission permission="users:read">
                    <UsersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/auditoria"
                element={
                  <RequirePermission permission="audit:read">
                    <AuditPage />
                  </RequirePermission>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
