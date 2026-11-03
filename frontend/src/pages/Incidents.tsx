import { useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, Siren } from "lucide-react";
import { useIncidents, useUpdateIncident } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, EmptyState, ErrorNote, SeverityBadge, Spinner } from "../components/ui";
import { fmtDateTime, timeAgo } from "../lib/format";
import type { Incident } from "../api/types";

const STATUSES: Incident["status"][] = ["open", "investigating", "contained", "eradicated", "recovered", "closed"];

const STATUS_LABEL: Record<Incident["status"], string> = {
  open: "Abierto",
  investigating: "En investigación",
  contained: "Contenido",
  eradicated: "Erradicado",
  recovered: "Recuperado",
  closed: "Cerrado",
};

export function IncidentsPage() {
  const { can } = useAuth();
  const [onlyOverdue, setOnlyOverdue] = useState(false);
  const { data, isLoading, error } = useIncidents(onlyOverdue ? { overdue: true } : {});
  const updateIncident = useUpdateIncident();
  const [failure, setFailure] = useState<string | null>(null);

  async function changeStatus(incident: Incident, status: Incident["status"]) {
    setFailure(null);
    try {
      await updateIncident.mutateAsync({
        id: incident.id,
        payload: {
          status,
          resolution: status === "closed" ? incident.resolution ?? "Cierre operativo registrado desde el panel." : undefined,
        },
      });
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-[#343C6A] tracking-tight">Gestión de Incidentes</h1>
          <p className="text-xs font-medium text-[#718EBF] mt-0.5">Seguimiento de respuesta, contención y cumplimiento de SLAs</p>
        </div>
        <label className="flex items-center gap-2.5 text-xs font-bold text-[#718EBF] bg-white px-4 py-2 rounded-2xl border border-[#E6EFF5] cursor-pointer hover:border-[#2D60FF]/30 transition shadow-xs">
          <input
            type="checkbox"
            checked={onlyOverdue}
            onChange={(event) => setOnlyOverdue(event.target.checked)}
            className="h-4 w-4 rounded-lg border-[#DFEAF2] text-[#2D60FF] focus:ring-[#2D60FF]"
          />
          Solo SLA Vencidos
        </label>
      </header>

      {failure && <ErrorNote message={failure} />}
      {error && <ErrorNote message={apiErrorMessage(error)} />}

      {isLoading ? (
        <Spinner />
      ) : !data || data.length === 0 ? (
        <Card>
          <EmptyState title="Sin incidentes registrados" hint="Los incidentes se abren al escalar alertas críticas o sospechosas." />
        </Card>
      ) : (
        <div className="grid gap-4">
          {data.map((incident) => {
            const overdue = new Date(incident.sla_due_at) < new Date() && incident.status !== "closed";
            return (
              <Card key={incident.id} noPadding className="p-6 sm:p-7">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[#EDF2FF] px-2.5 py-0.5 font-mono text-xs font-bold text-[#2D60FF]">
                        {incident.code}
                      </span>
                      <SeverityBadge severity={incident.severity} />
                      <span className="text-xs font-bold text-[#718EBF] bg-[#F5F7FA] px-2.5 py-0.5 rounded-full border border-[#DFEAF2]">
                        {STATUS_LABEL[incident.status]}
                      </span>
                      {overdue && (
                        <span className="flex items-center gap-1 rounded-full bg-[#FFF0F2] border border-[#FFCCD4] px-2.5 py-0.5 text-xs font-bold text-[#FE5C73]">
                          <Clock3 size={12} /> SLA Vencido
                        </span>
                      )}
                    </div>
                    <h2 className="mt-2.5 text-base sm:text-lg font-bold text-[#343C6A]">{incident.title}</h2>
                    <p className="mt-1 text-xs font-medium text-[#718EBF]">
                      Abierto {timeAgo(incident.opened_at)} · vence {fmtDateTime(incident.sla_due_at)}
                      {incident.ticket_ref ? ` · Ticket ${incident.ticket_ref}` : ""}
                    </p>
                    {incident.resolution && (
                      <p className="mt-3 rounded-2xl bg-[#F5F7FA] border border-[#E6EFF5] p-3 text-xs font-medium text-[#343C6A]">
                        {incident.resolution}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/alertas?incidente=${incident.code}`}
                      className="rounded-2xl border border-[#DFEAF2] bg-white px-3.5 py-2 text-xs font-semibold text-[#343C6A] hover:bg-[#F5F7FA] hover:border-[#2D60FF]/30 transition"
                    >
                      <Siren size={14} className="mr-1.5 inline text-[#2D60FF]" /> Ver Alertas
                    </Link>
                    {can("incidents:update") && incident.status !== "closed" && (
                      <select
                        value={incident.status}
                        onChange={(event) => void changeStatus(incident, event.target.value as Incident["status"])}
                        className="rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3 py-2 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                      >
                        {STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {STATUS_LABEL[status]}
                          </option>
                        ))}
                      </select>
                    )}
                    {can("incidents:close") && incident.status !== "closed" && (
                      <Button size="sm" variant="secondary" onClick={() => void changeStatus(incident, "closed")} className="text-xs py-2">
                        Cerrar
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
