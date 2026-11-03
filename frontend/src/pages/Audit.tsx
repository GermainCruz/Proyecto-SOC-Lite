import { useState, type FormEvent } from "react";
import { ShieldCheck, ShieldX } from "lucide-react";
import { useAudit, useVerifyChain } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { Button, Card, EmptyState, ErrorNote, Spinner } from "../components/ui";
import { fmtDateTime } from "../lib/format";

const MODULES = ["", "auth", "alerts", "triage", "incidents", "reports", "users", "audit", "dashboard"];

const RESULT_LABEL: Record<string, string> = {
  success: "Éxito",
  denied: "Denegado",
  error: "Error",
};

export function AuditPage() {
  const [module, setModule] = useState("");
  const [result, setResult] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useAudit({
    page,
    page_size: 50,
    ...(module ? { module } : {}),
    ...(result ? { result } : {}),
    ...(userEmail ? { user_email: userEmail } : {}),
  });
  const verify = useVerifyChain();

  function onFilter(event: FormEvent) {
    event.preventDefault();
    setPage(1);
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-[#343C6A] tracking-tight">Bitácora de Auditoría</h1>
          <p className="text-xs font-medium text-[#718EBF] mt-0.5">
            Registro append-only inmutable por módulo con verificación criptográfica SHA-256.
          </p>
        </div>
        <Button variant="primary" onClick={() => verify.mutate()} disabled={verify.isPending} className="text-xs">
          <ShieldCheck size={16} />
          {verify.isPending ? "Verificando cadena…" : "Verificar Integridad SHA-256"}
        </Button>
      </header>

      {verify.data && (
        <div
          className={
            verify.data.intact
              ? "flex items-center gap-2.5 rounded-2xl border border-[#B7F4EE] bg-[#E7FAF8] px-4 py-3 text-sm font-semibold text-[#16DBCC]"
              : "flex items-center gap-2.5 rounded-2xl border border-[#FFCCD4] bg-[#FFF0F2] px-4 py-3 text-sm font-semibold text-[#FE5C73]"
          }
        >
          {verify.data.intact ? <ShieldCheck size={18} /> : <ShieldX size={18} />}
          {verify.data.intact
            ? `Cadena criptográfica íntegra: ${verify.data.total} eventos verificados matemáticamente.`
            : `Alerta: Se detectaron ${verify.data.broken} registros alterados de un total de ${verify.data.total}.`}
        </div>
      )}

      {verify.error && <ErrorNote message={apiErrorMessage(verify.error)} />}

      <Card noPadding className="p-5 sm:p-6">
        <form onSubmit={onFilter} className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:flex lg:flex-wrap lg:items-end">
          <label className="flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Módulo</span>
            <select
              value={module}
              onChange={(event) => setModule(event.target.value)}
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            >
              {MODULES.map((value) => (
                <option key={value || "all"} value={value}>
                  {value || "Todos"}
                </option>
              ))}
            </select>
          </label>
          <label className="flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Resultado</span>
            <select
              value={result}
              onChange={(event) => setResult(event.target.value)}
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            >
              <option value="">Todos</option>
              <option value="success">Éxito</option>
              <option value="denied">Denegado</option>
              <option value="error">Error</option>
            </select>
          </label>
          <label className="min-w-[200px] flex-1 sm:col-span-2 md:col-span-4 lg:flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Usuario</span>
            <input
              value={userEmail}
              onChange={(event) => setUserEmail(event.target.value)}
              placeholder="correo@empresa..."
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            />
          </label>
          <Button type="submit" variant="secondary" className="w-full lg:w-auto text-xs py-2.5">
            Filtrar
          </Button>
        </form>
      </Card>

      {error && <ErrorNote message={apiErrorMessage(error)} />}

      <Card noPadding className="overflow-hidden">
        {isLoading ? (
          <Spinner />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="Sin eventos para los filtros seleccionados" />
        ) : (
          <>
            {/* Vista móvil: tarjetas responsivas estilo BankDash */}
            <div className="divide-y divide-[#F0F5FA] md:hidden">
              {data.items.map((entry) => (
                <div key={`${entry.id}-${entry.occurred_at}`} className="p-5 space-y-2 hover:bg-[#F5F7FA]/60 transition">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-[#2D60FF] bg-[#EDF2FF] px-2.5 py-0.5 rounded-full">
                      {entry.module}
                    </span>
                    <span
                      className={
                        entry.result === "success"
                          ? "rounded-full bg-[#E7FAF8] border border-[#B7F4EE] px-2.5 py-0.5 text-xs font-bold text-[#16DBCC]"
                          : entry.result === "denied"
                            ? "rounded-full bg-[#FFF5D9] border border-[#FFE8AA] px-2.5 py-0.5 text-xs font-bold text-[#FEAA09]"
                            : "rounded-full bg-[#FFF0F2] border border-[#FFCCD4] px-2.5 py-0.5 text-xs font-bold text-[#FE5C73]"
                      }
                    >
                      {RESULT_LABEL[entry.result] ?? entry.result}
                    </span>
                  </div>

                  <p className="font-mono text-xs text-[#343C6A] font-bold">
                    {entry.action}
                  </p>

                  <div className="flex items-center justify-between text-xs text-[#718EBF] pt-1">
                    <span>
                      <strong className="text-[#343C6A]">{entry.user_email ?? "sistema"}</strong>{" "}
                      <span className="text-[10px] uppercase font-semibold text-[#8BA3CB]">({entry.role_code ?? "—"})</span>
                    </span>
                    <span className="font-mono text-[#8BA3CB]">{entry.ip_address ?? "—"}</span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-[#718EBF] pt-1 border-t border-[#F0F5FA]">
                    <span className="truncate">Entidad: {entry.entity ?? "—"} {entry.entity_id ? `(${entry.entity_id.slice(0, 10)}…)` : ""}</span>
                    <span className="flex-none font-medium">{fmtDateTime(entry.occurred_at)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Vista escritorio: tabla completa */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="border-b border-[#F0F5FA] text-left text-xs uppercase font-bold tracking-wider text-[#718EBF]">
                  <tr>
                    <th className="px-5 py-4">Fecha y Hora</th>
                    <th className="px-5 py-4">Usuario</th>
                    <th className="px-5 py-4">Acción</th>
                    <th className="px-5 py-4">Entidad</th>
                    <th className="px-5 py-4">Resultado</th>
                    <th className="px-5 py-4">IP Origen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0F5FA]">
                  {data.items.map((entry) => (
                    <tr key={`${entry.id}-${entry.occurred_at}`} className="hover:bg-[#F5F7FA]/70 transition">
                      <td className="whitespace-nowrap px-5 py-3.5 text-xs font-medium text-[#718EBF]">
                        {fmtDateTime(entry.occurred_at)}
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="text-xs font-bold text-[#343C6A]">{entry.user_email ?? "sistema"}</p>
                        <p className="text-[11px] uppercase font-semibold text-[#718EBF]">{entry.role_code ?? "—"}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="font-mono text-xs font-bold text-[#2D60FF]">{entry.action}</p>
                        <p className="text-[11px] font-medium text-[#718EBF]">{entry.module}</p>
                      </td>
                      <td className="px-5 py-3.5 text-xs font-medium text-[#343C6A]">
                        {entry.entity ?? "—"}
                        {entry.entity_id && (
                          <span className="block truncate font-mono text-[10px] text-[#718EBF]">
                            {entry.entity_id.slice(0, 18)}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={
                            entry.result === "success"
                              ? "rounded-full bg-[#E7FAF8] border border-[#B7F4EE] px-2.5 py-0.5 text-xs font-bold text-[#16DBCC]"
                              : entry.result === "denied"
                                ? "rounded-full bg-[#FFF5D9] border border-[#FFE8AA] px-2.5 py-0.5 text-xs font-bold text-[#FEAA09]"
                                : "rounded-full bg-[#FFF0F2] border border-[#FFCCD4] px-2.5 py-0.5 text-xs font-bold text-[#FE5C73]"
                          }
                        >
                          {RESULT_LABEL[entry.result] ?? entry.result}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-[#718EBF]">{entry.ip_address ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-[#F0F5FA] px-5 py-4 text-xs font-semibold text-[#718EBF]">
              <span>{data.total} eventos registrados · Página {data.page}</span>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Anterior
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={page * data.page_size >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
