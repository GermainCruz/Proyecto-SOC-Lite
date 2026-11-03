import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bot, CheckCircle2, RefreshCw, Siren, TriangleAlert } from "lucide-react";
import { useAlert, useEscalateAlert, useReviewTriage, useRunTriage, useUpdateAlert } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Button,
  Card,
  ErrorNote,
  SeverityBadge,
  Spinner,
  StatusBadge,
  VerdictBadge,
} from "../components/ui";
import { fmtDateTime, timeAgo } from "../lib/format";

const VERDICTS = [
  { value: "true_positive", label: "Verdadero positivo" },
  { value: "suspicious", label: "Sospechoso" },
  { value: "benign", label: "Benigno" },
  { value: "false_positive", label: "Falso positivo" },
];

export function AlertDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { data: alert, isLoading, error } = useAlert(id);
  const updateAlert = useUpdateAlert();
  const runTriage = useRunTriage();
  const reviewTriage = useReviewTriage();
  const escalate = useEscalateAlert();

  const [reviewVerdict, setReviewVerdict] = useState("true_positive");
  const [comment, setComment] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  if (isLoading) return <Spinner label="Cargando alerta…" />;
  if (error || !alert) return <ErrorNote message={apiErrorMessage(error)} />;

  const triage = alert.triage_results[0] ?? null;

  async function handleRunTriage(force: boolean) {
    if (!id) return;
    setFailure(null);
    try {
      await runTriage.mutateAsync({ id, force });
      setFeedback(force ? "Triaje re-ejecutado." : "Triaje ejecutado.");
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function handleReview() {
    if (!id) return;
    if (comment.trim().length < 5) {
      setFailure("El comentario de validación debe tener al menos 5 caracteres.");
      return;
    }
    setFailure(null);
    try {
      await reviewTriage.mutateAsync({ id, verdict: reviewVerdict, comment });
      setFeedback("Veredicto registrado en la bitácora.");
      setComment("");
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function handleStatus(status: string) {
    if (!id) return;
    try {
      await updateAlert.mutateAsync({ id, payload: { status, comment: "Cambio desde detalle de alerta" } });
      setFeedback(`Estado actualizado a ${status}.`);
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function handleEscalate() {
    if (!id) return;
    try {
      const result = await escalate.mutateAsync(id);
      setFeedback(`Incidente ${result.code} creado.`);
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/alertas" className="inline-flex items-center gap-2 text-xs font-bold text-[#718EBF] hover:text-[#2D60FF] transition">
        <ArrowLeft size={16} /> Volver a la bandeja de alertas
      </Link>

      {/* Cabecera Principal de la Alerta */}
      <section className="rounded-3xl border border-[#E6EFF5] bg-white p-6 sm:p-8 shadow-[0_4px_24px_rgba(223,230,242,0.45)] flex flex-wrap items-center justify-between gap-6">
        <div className="max-w-3xl min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <SeverityBadge severity={alert.severity} />
            <StatusBadge status={alert.status} />
            {alert.incident_code && (
              <span className="rounded-full bg-[#FFF0F2] border border-[#FFCCD4] px-3 py-0.5 text-xs font-bold text-[#FE5C73]">
                Incidente {alert.incident_code}
              </span>
            )}
          </div>
          <h1 className="mt-3 text-2xl sm:text-3xl font-extrabold text-[#343C6A] tracking-tight">{alert.title}</h1>
          <p className="mt-2 text-xs sm:text-sm font-medium text-[#718EBF]">
            {alert.description ?? "Sin descripción adicional"} · Detectada {timeAgo(alert.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {can("triage:run") && (
            <Button variant="secondary" onClick={() => void handleRunTriage(Boolean(triage))} className="text-xs">
              <RefreshCw size={15} className={runTriage.isPending ? "animate-spin text-[#2D60FF]" : "text-[#2D60FF]"} />
              {triage ? "Re-ejecutar Triaje IA" : "Ejecutar Triaje IA"}
            </Button>
          )}
          {can("incidents:create") && (
            <Button variant="danger" onClick={() => void handleEscalate()} disabled={Boolean(alert.incident_code)} className="text-xs">
              <Siren size={15} /> Escalar a Incidente
            </Button>
          )}
        </div>
      </section>

      {(feedback || failure) && (
        <div className="space-y-2">
          {feedback && (
            <div className="flex items-center gap-2 rounded-2xl border border-[#B7F4EE] bg-[#E7FAF8] px-4 py-3 text-xs font-bold text-[#16DBCC]">
              <CheckCircle2 size={16} /> {feedback}
            </div>
          )}
          {failure && <ErrorNote message={failure} />}
        </div>
      )}

      {/* Grid Central: Datos del Evento + Triaje IA */}
      <div className="grid gap-6 xl:grid-cols-12 items-stretch">
        <Card
          title="Datos del Evento"
          subtitle="Telemetría técnica del sensor"
          className="xl:col-span-5"
          contentClassName="justify-between space-y-6"
        >
          <dl className="divide-y divide-[#F0F5FA] text-xs font-medium">
            {[
              ["Fuente", alert.source ?? "—"],
              ["Regla", `${alert.rule_id ?? "N/D"} (nivel ${alert.rule_level ?? "—"})`],
              ["Activo", alert.agent_name ?? "—"],
              ["Criticidad", alert.asset?.criticality ?? "—"],
              ["IP Origen", alert.src_ip ?? "—"],
              ["IP Destino", alert.dst_ip ?? "—"],
              ["Táctica MITRE", alert.mitre_tactic ?? "—"],
              ["Técnica MITRE", alert.mitre_technique ?? "—"],
              ["Repeticiones", String(alert.dedup_count)],
              ["Primera Detección", fmtDateTime(alert.first_seen_at)],
              ["Última Detección", fmtDateTime(alert.last_seen_at)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between items-center py-2.5">
                <dt className="text-[#718EBF] font-semibold">{label}</dt>
                <dd className="text-right font-bold text-[#343C6A] font-mono">{value}</dd>
              </div>
            ))}
          </dl>

          {can("alerts:update") && (
            <div className="pt-5 border-t border-[#F0F5FA]">
              <label className="block">
                <span className="mb-2 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Cambiar Estado</span>
                <select
                  value={alert.status}
                  onChange={(event) => void handleStatus(event.target.value)}
                  className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-3 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                >
                  {["pending", "triaged", "in_review", "escalated", "closed", "false_positive", "suppressed"].map(
                    (status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ),
                  )}
                </select>
              </label>
            </div>
          )}
        </Card>

        <Card
          title={
            <span className="flex items-center gap-2.5">
              <Bot size={20} className="text-[#2D60FF]" /> Triaje Asistido por IA (Llama 3.1)
            </span>
          }
          subtitle={triage ? `${triage.model} · prompt ${triage.prompt_version}` : "Sin triaje registrado"}
          className="xl:col-span-7"
          contentClassName="space-y-6 justify-between"
        >
          {!triage ? (
            <div className="rounded-2xl border border-dashed border-[#DFEAF2] p-12 text-center text-xs font-medium text-[#718EBF] my-auto">
              Esta alerta aún no fue procesada por el motor de triaje.
            </div>
          ) : (
            <div className="space-y-6 flex-1 flex flex-col justify-between">
              <div className="space-y-5">
                {/* Badges de Veredicto y Severidad */}
                <div className="flex flex-wrap items-center gap-3 pb-4 border-b border-[#F0F5FA]">
                  <VerdictBadge verdict={triage.human_verdict ?? triage.verdict} confidence={triage.confidence} />
                  <span className="text-xs font-medium text-[#718EBF]">
                    Severidad sugerida: <strong className="text-[#343C6A] uppercase font-bold">{triage.suggested_severity}</strong>
                  </span>
                  {triage.needs_human_review && (
                    <span className="flex items-center gap-1.5 rounded-full bg-[#FFF5D9] border border-[#FFE8AA] px-3 py-1 text-xs font-bold text-[#FEAA09]">
                      <TriangleAlert size={13} /> Requiere Revisión Humana
                    </span>
                  )}
                  <span className="text-xs text-[#8BA3CB] ml-auto">{fmtDateTime(triage.created_at)}</span>
                </div>

                {/* Dictamen del Modelo */}
                <div className="rounded-2xl border border-[#E6EFF5] bg-[#F5F7FA] p-5">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#718EBF] mb-2 flex items-center gap-1.5">
                    <Bot size={15} className="text-[#2D60FF]" /> Dictamen y Resumen
                  </p>
                  <p className="text-sm leading-relaxed text-[#343C6A] font-medium">
                    {triage.summary}
                  </p>
                </div>

                {/* Acciones Recomendadas */}
                <div>
                  <p className="mb-3 text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                    Acciones Recomendadas por la IA
                  </p>
                  <ol className="space-y-2.5">
                    {triage.recommended_actions.map((action, index) => (
                      <li key={action} className="flex items-center gap-3 text-xs font-semibold text-[#343C6A] bg-[#F8FAFC] px-4 py-3 rounded-2xl border border-[#EDF2F7]">
                        <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-[#2D60FF] text-[11px] font-bold text-white shadow-xs">
                          {index + 1}
                        </span>
                        <span className="leading-snug">{action}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                {/* Técnicas MITRE */}
                {triage.mitre_techniques.length > 0 && (
                  <div>
                    <p className="mb-2.5 text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                      Técnicas MITRE ATT&CK Identificadas
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {triage.mitre_techniques.map((technique) => (
                        <a
                          key={technique}
                          href={`https://attack.mitre.org/techniques/${technique.replace(".", "/")}/`}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-full bg-[#EDF2FF] border border-[#D5E2FF] px-3.5 py-1 font-mono text-xs font-bold text-[#2D60FF] hover:bg-[#2D60FF] hover:text-white transition"
                        >
                          {technique}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Panel de Validación del Analista (Con grid responsive que no desborda) */}
              {can("triage:review") && (
                <div className="rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] p-5 mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#343C6A] mb-3">
                    Validación del Analista (Human-in-the-Loop)
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
                    <div className="sm:col-span-4">
                      <select
                        value={reviewVerdict}
                        onChange={(event) => setReviewVerdict(event.target.value)}
                        className="w-full rounded-xl border border-[#DFEAF2] bg-white px-3.5 py-2.5 text-xs font-bold text-[#343C6A] outline-none focus:border-[#2D60FF]"
                      >
                        {VERDICTS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="sm:col-span-5">
                      <input
                        value={comment}
                        onChange={(event) => setComment(event.target.value)}
                        placeholder="Comentario de validación..."
                        className="w-full rounded-xl border border-[#DFEAF2] bg-white px-3.5 py-2.5 text-xs font-medium text-[#343C6A] outline-none focus:border-[#2D60FF]"
                      />
                    </div>
                    <div className="sm:col-span-3">
                      <Button
                        onClick={() => void handleReview()}
                        disabled={reviewTriage.isPending}
                        className="w-full text-xs py-2.5 whitespace-nowrap"
                      >
                        Registrar Veredicto
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Enriquecimiento de Indicadores" subtitle="Evidencia e IOCs analizados por el modelo">
          {alert.enrichments.length === 0 ? (
            <p className="text-xs font-medium text-[#718EBF]">Sin enriquecimiento externo disponible.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead className="text-left font-bold uppercase tracking-wider text-[#718EBF] border-b border-[#F0F5FA]">
                  <tr>
                    <th className="py-2.5">Proveedor</th>
                    <th className="py-2.5">Indicador</th>
                    <th className="py-2.5">Veredicto</th>
                    <th className="py-2.5">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0F5FA]">
                  {alert.enrichments.map((enrichment) => (
                    <tr key={`${enrichment.provider}-${enrichment.indicator}`}>
                      <td className="py-2.5 font-bold text-[#343C6A]">{enrichment.provider}</td>
                      <td className="py-2.5 font-mono text-xs text-[#718EBF]">{enrichment.indicator}</td>
                      <td className="py-2.5 font-semibold text-[#343C6A]">{enrichment.verdict ?? "—"}</td>
                      <td className="py-2.5 font-bold text-[#2D60FF] tabular-nums">{enrichment.score ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Evento Original" subtitle="Payload crudo recibido del sensor / SIEM">
          <details>
            <summary className="cursor-pointer text-xs font-bold text-[#2D60FF] hover:underline">
              Ver JSON completo recibido
            </summary>
            <pre className="mt-3 max-h-80 overflow-auto rounded-2xl bg-[#1E293B] p-4 text-xs font-mono text-[#F1F5F9]">
              {JSON.stringify(alert.raw_payload, null, 2)}
            </pre>
          </details>
        </Card>
      </div>
    </div>
  );
}
