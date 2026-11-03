import { useState, type FormEvent } from "react";
import { UserPlus } from "lucide-react";
import { useCreateUser, useUpdateUser, useUsers } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, EmptyState, ErrorNote, Spinner } from "../components/ui";
import { fmtDateTime } from "../lib/format";

const ROLES = [
  { code: "admin", label: "Administrador" },
  { code: "soc_manager", label: "Jefe de SOC" },
  { code: "analyst", label: "Analista SOC" },
  { code: "auditor", label: "Auditor" },
  { code: "viewer", label: "Directivo / Consulta" },
];

export function UsersPage() {
  const { can } = useAuth();
  const { data, isLoading, error } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    role_code: "analyst",
    area: "",
    password: "",
  });
  const [feedback, setFeedback] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setFailure(null);
    setFeedback(null);
    try {
      await createUser.mutateAsync({ ...form, area: form.area || null });
      setFeedback(`Usuario ${form.email} creado.`);
      setForm({ full_name: "", email: "", role_code: "analyst", area: "", password: "" });
      setShowForm(false);
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function toggleActive(id: string, isActive: boolean) {
    setFailure(null);
    try {
      await updateUser.mutateAsync({ id, payload: { is_active: !isActive } });
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function changeRole(id: string, roleCode: string) {
    setFailure(null);
    try {
      await updateUser.mutateAsync({ id, payload: { role_code: roleCode } });
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-[#343C6A] tracking-tight">Usuarios y Permisos (RBAC)</h1>
          <p className="text-xs font-medium text-[#718EBF] mt-0.5">
            Control de acceso basado en roles. Toda asignación y cambio de estado queda auditado en la cadena SHA-256.
          </p>
        </div>
        {can("users:create") && (
          <Button onClick={() => setShowForm((value) => !value)} className="text-xs">
            <UserPlus size={16} /> {showForm ? "Ocultar Formulario" : "Nuevo Usuario"}
          </Button>
        )}
      </header>

      {feedback && (
        <div className="rounded-2xl border border-[#B7F4EE] bg-[#E7FAF8] px-4 py-3 text-xs font-bold text-[#16DBCC]">
          {feedback}
        </div>
      )}
      {failure && <ErrorNote message={failure} />}
      {error && <ErrorNote message={apiErrorMessage(error)} />}

      {showForm && (
        <Card title="Crear Nuevo Usuario" subtitle="Contraseña mínima de 12 caracteres con mayúscula, símbolo y dígito">
          <form onSubmit={onCreate} className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Nombre Completo</span>
              <input
                required
                minLength={3}
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Correo Electrónico</span>
              <input
                required
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Rol Asignado</span>
              <select
                value={form.role_code}
                onChange={(event) => setForm({ ...form, role_code: event.target.value })}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
              >
                {ROLES.map((role) => (
                  <option key={role.code} value={role.code}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Área / Departamento</span>
              <input
                value={form.area}
                onChange={(event) => setForm({ ...form, area: event.target.value })}
                placeholder="ej. SOC Tier 1, Auditoría..."
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Contraseña Temporal</span>
              <input
                required
                type="password"
                minLength={12}
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
              />
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={createUser.isPending} className="py-2.5 text-xs">
                {createUser.isPending ? "Creando usuario…" : "Registrar Usuario"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-hidden p-0">
        {isLoading ? (
          <Spinner />
        ) : !data || data.length === 0 ? (
          <EmptyState title="Sin usuarios registrados" />
        ) : (
          <>
            {/* Vista móvil: tarjetas responsivas */}
            <div className="divide-y divide-[#F0F5FA] md:hidden">
              {data.map((user) => (
                <div key={user.id} className="p-4.5 space-y-2.5 hover:bg-[#F5F7FA]/60 transition">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="font-bold text-[#343C6A] text-sm">{user.full_name}</p>
                      <p className="text-xs text-[#718EBF] font-medium">{user.email}</p>
                    </div>
                    <button
                      disabled={!can("users:update")}
                      onClick={() => void toggleActive(user.id, user.is_active)}
                      className={
                        user.is_active
                          ? "rounded-full bg-[#E7FAF8] border border-[#B7F4EE] px-3 py-1 text-xs font-bold text-[#16DBCC]"
                          : "rounded-full bg-[#F5F7FA] border border-[#DFEAF2] px-3 py-1 text-xs font-bold text-[#718EBF]"
                      }
                    >
                      {user.is_active ? "Activo" : "Inactivo"}
                    </button>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs text-[#718EBF]">
                    <div>
                      <span className="font-bold text-[#718EBF] mr-1.5 uppercase text-[10px]">Rol:</span>
                      {can("users:update") ? (
                        <select
                          value={user.role.code}
                          onChange={(event) => void changeRole(user.id, event.target.value)}
                          className="rounded-xl border border-[#DFEAF2] bg-[#F5F7FA] px-2.5 py-1 text-xs font-bold text-[#343C6A] outline-none"
                        >
                          {ROLES.map((role) => (
                            <option key={role.code} value={role.code}>
                              {role.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="font-bold text-[#343C6A]">{user.role.name}</span>
                      )}
                    </div>
                    <div>
                      <span className="font-bold text-[#718EBF] mr-1 uppercase text-[10px]">Área:</span>
                      <span className="font-semibold text-[#343C6A]">{user.area ?? "—"}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-[#718EBF] pt-2 border-t border-[#F0F5FA]">
                    <span>MFA: {user.mfa_enabled ? <strong className="text-[#16DBCC]">Activo</strong> : "Inactivo"}</span>
                    <span>Acceso: {fmtDateTime(user.last_login_at)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Vista escritorio: tabla */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="border-b border-[#F0F5FA] text-left text-xs uppercase font-bold tracking-wider text-[#718EBF]">
                  <tr>
                    <th className="px-5 py-4">Usuario</th>
                    <th className="px-5 py-4">Rol Asignado</th>
                    <th className="px-5 py-4">Área</th>
                    <th className="px-5 py-4">MFA</th>
                    <th className="px-5 py-4">Último Acceso</th>
                    <th className="px-5 py-4">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0F5FA]">
                  {data.map((user) => (
                    <tr key={user.id} className="hover:bg-[#F5F7FA]/70 transition">
                      <td className="px-5 py-3.5">
                        <p className="font-bold text-[#343C6A]">{user.full_name}</p>
                        <p className="text-xs text-[#718EBF] font-medium">{user.email}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        {can("users:update") ? (
                          <select
                            value={user.role.code}
                            onChange={(event) => void changeRole(user.id, event.target.value)}
                            className="rounded-xl border border-[#DFEAF2] bg-[#F5F7FA] px-2.5 py-1 text-xs font-bold text-[#343C6A] outline-none focus:border-[#2D60FF]"
                          >
                            {ROLES.map((role) => (
                              <option key={role.code} value={role.code}>
                                {role.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-xs font-bold text-[#343C6A]">{user.role.name}</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-xs font-semibold text-[#718EBF]">{user.area ?? "—"}</td>
                      <td className="px-5 py-3.5 text-xs font-bold">
                        {user.mfa_enabled ? (
                          <span className="text-[#16DBCC]">Activo</span>
                        ) : (
                          <span className="text-[#8BA3CB]">Inactivo</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-xs font-medium text-[#718EBF]">{fmtDateTime(user.last_login_at)}</td>
                      <td className="px-5 py-3.5">
                        <button
                          disabled={!can("users:update")}
                          onClick={() => void toggleActive(user.id, user.is_active)}
                          className={
                            user.is_active
                              ? "rounded-full bg-[#E7FAF8] border border-[#B7F4EE] px-3 py-1 text-xs font-bold text-[#16DBCC]"
                              : "rounded-full bg-[#F5F7FA] border border-[#DFEAF2] px-3 py-1 text-xs font-bold text-[#718EBF]"
                          }
                        >
                          {user.is_active ? "Activo" : "Inactivo"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

