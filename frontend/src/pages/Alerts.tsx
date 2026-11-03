import { useState } from "react";
import { Link } from "react-router-dom";
import { Filter, Search, X } from "lucide-react";
import { useAlerts, type AlertFilters } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { Button, Card, EmptyState, ErrorNote, SeverityBadge, Spinner, StatusBadge, VerdictBadge } from "../components/ui";
import { fmtDateTime, timeAgo } from "../lib/format";
import type { Severity } from "../api/types";

const SEVERITIES: (Severity | "")[] = ["", "critical", "high", "medium", "low", "info"];
const STATUSES = ["", "pending", "triaged", "in_review", "escalated", "false_positive", "closed"];
const SOURCES = ["", "wazuh", "opnsense", "suricata", "manual"];

export function AlertsPage() {
  const [filters, setFilters] = useState<AlertFilters>({
    page: 1,
    page_size: 25,
    severity: "",
    status: "",
    source: "",
    q: "",
    sort: "-created_at",
  });
  const [search, setSearch] = useState("");
  const { data, isLoading, error, isFetching } = useAlerts(filters);

  function update(patch: Partial<AlertFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-[#343C6A] tracking-tight">Alertas de Seguridad</h1>
          <p className="text-xs font-medium text-[#718EBF] mt-0.5">
            {data ? `${data.total} alertas registradas en el periodo filtrado` : "Bandeja de triaje y respuesta"}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-[#718EBF] bg-white px-3.5 py-1.5 rounded-full border border-[#E6EFF5]">
          <Filter size={14} className="text-[#2D60FF]" /> {isFetching ? "Actualizando…" : "Filtros activos"}
        </div>
      </header>

      <Card noPadding className="p-5 sm:p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:flex lg:flex-wrap lg:items-end">
          <label className="min-w-[200px] flex-1 sm:col-span-2 md:col-span-4 lg:flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Buscar</span>
            <div className="flex items-center gap-2.5 rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 focus-within:ring-2 focus-within:ring-[#2D60FF]/20 focus-within:bg-white focus-within:border-[#2D60FF] transition">
              <Search size={16} className="text-[#718EBF]" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") update({ q: search });
                }}
                placeholder="Título, regla o activo..."
                className="w-full border-0 bg-transparent text-xs font-semibold text-[#343C6A] outline-none placeholder-[#8BA3CB]"
              />
              {search && (
                <button
                  onClick={() => {
                    setSearch("");
                    update({ q: "" });
                  }}
                  aria-label="Limpiar búsqueda"
                  className="text-[#718EBF] hover:text-[#343C6A]"
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </label>

          <label className="flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Severidad</span>
            <select
              value={filters.severity}
              onChange={(event) => update({ severity: event.target.value as Severity | "" })}
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            >
              {SEVERITIES.map((value) => (
                <option key={value || "all"} value={value}>
                  {value === "" ? "Todas" : value}
                </option>
              ))}
            </select>
          </label>

          <label className="flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Estado</span>
            <select
              value={filters.status}
              onChange={(event) => update({ status: event.target.value })}
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            >
              {STATUSES.map((value) => (
                <option key={value || "all"} value={value}>
                  {value === "" ? "Todos" : value}
                </option>
              ))}
            </select>
          </label>

          <label className="flex-1">
            <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Fuente</span>
            <select
              value={filters.source}
              onChange={(event) => update({ source: event.target.value })}
              className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
            >
              {SOURCES.map((value) => (
                <option key={value || "all"} value={value}>
                  {value === "" ? "Todas" : value}
                </option>
              ))}
            </select>
          </label>

          <Button variant="secondary" onClick={() => update({ q: search })} className="w-full lg:w-auto text-xs py-2.5">
            Aplicar
          </Button>
        </div>
      </Card>

      {error && <ErrorNote message={apiErrorMessage(error)} />}

      <Card noPadding className="overflow-hidden">
        {isLoading ? (
          <Spinner />
        ) : !data || data.items.length === 0 ? (
          <EmptyState title="Sin alertas para los filtros seleccionados" hint="Pruebe ampliando el periodo o la severidad." />
        ) : (
          <>
            {/* Vista móvil: tarjetas responsivas estilo BankDash */}
            <div className="divide-y divide-[#F0F5FA] md:hidden">
              {data.items.map((alert) => {
                const lastTriage = alert.latest_triage;
                return (
                  <div key={alert.id} className="p-5 space-y-3 hover:bg-[#F5F7FA]/60 transition">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={alert.severity} />
                        <StatusBadge status={alert.status} />
                      </div>
                      <span className="text-[11px] font-medium text-[#718EBF]">{timeAgo(alert.created_at)}</span>
                    </div>

                    <Link to={`/alertas/${alert.id}`} className="block font-bold text-[#343C6A] hover:text-[#2D60FF] text-sm leading-snug transition">
                      {alert.title}
                    </Link>

                    <div className="flex flex-wrap items-center justify-between gap-y-1 gap-x-3 text-xs text-[#718EBF] pt-1">
                      <span>{alert.agent_name ?? "—"} <span className="font-mono text-[#8BA3CB]">({alert.src_ip ?? "interno"})</span></span>
                      <span className="font-semibold">Regla {alert.rule_id ?? "N/D"}</span>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <div>
                        {lastTriage ? (
                          <VerdictBadge verdict={lastTriage.verdict} confidence={lastTriage.confidence} />
                        ) : (
                          <span className="text-xs font-semibold text-[#718EBF] bg-[#F5F7FA] px-2 py-0.5 rounded-full">Sin triaje</span>
                        )}
                      </div>
                      <span className="text-[11px] font-medium text-[#718EBF]">{fmtDateTime(alert.created_at)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Vista de escritorio: tabla completa */}
            <div className="hidden md:block overflow-x-auto scrollbar-thin">
              <table className="table-sticky min-w-full text-sm">
                <thead className="border-b border-[#F0F5FA] text-left text-xs uppercase font-bold tracking-wider text-[#718EBF]">
                  <tr>
                    <th className="px-5 py-4">Severidad</th>
                    <th className="px-5 py-4">Alerta</th>
                    <th className="px-5 py-4">Activo / Origen</th>
                    <th className="px-5 py-4">Veredicto IA</th>
                    <th className="px-5 py-4">Estado</th>
                    <th className="px-5 py-4">Detectada</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0F5FA]">
                  {data.items.map((alert) => {
                    const lastTriage = alert.latest_triage;
                    return (
                      <tr key={alert.id} className="transition hover:bg-[#F5F7FA]/70">
                        <td className="px-5 py-3.5">
                          <SeverityBadge severity={alert.severity} />
                        </td>
                        <td className="px-5 py-3.5">
                          <Link to={`/alertas/${alert.id}`} className="font-bold text-[#343C6A] hover:text-[#2D60FF] transition">
                            {alert.title}
                          </Link>
                          <p className="mt-0.5 text-xs text-[#718EBF]">
                            Regla {alert.rule_id ?? "N/D"} · nivel {alert.rule_level ?? "—"} ·{" "}
                            {alert.dedup_count > 1 ? `${alert.dedup_count} repeticiones` : "1 evento"}
                          </p>
                        </td>
                        <td className="px-5 py-3.5">
                          <p className="font-semibold text-[#343C6A]">{alert.agent_name ?? "—"}</p>
                          <p className="font-mono text-xs text-[#718EBF]">{alert.src_ip ?? "interno"}</p>
                        </td>
                        <td className="px-5 py-3.5">
                          {lastTriage ? (
                            <VerdictBadge verdict={lastTriage.verdict} confidence={lastTriage.confidence} />
                          ) : (
                            <span className="text-xs font-semibold text-[#718EBF]">Pendiente</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusBadge status={alert.status} />
                        </td>
                        <td className="px-5 py-3.5 text-xs text-[#718EBF]">
                          <p className="font-semibold text-[#343C6A]">{fmtDateTime(alert.created_at)}</p>
                          <p className="text-[#8BA3CB]">{timeAgo(alert.created_at)}</p>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-xs font-semibold text-[#718EBF]">
          <span>
            Página {data.page} de {data.pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={data.page <= 1}
              onClick={() => update({ page: data.page - 1 })}
            >
              Anterior
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={data.page >= data.pages}
              onClick={() => update({ page: data.page + 1 })}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

