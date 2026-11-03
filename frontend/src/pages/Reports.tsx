import { useState, type FormEvent } from "react";
import { Download, FileSpreadsheet, FileText, FileType2, Plus } from "lucide-react";
import { downloadReport, useGenerateReport, useReports } from "../api/queries";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, EmptyState, ErrorNote, Spinner } from "../components/ui";
import { fmtBytes, fmtDate, fmtDateTime } from "../lib/format";
import type { Report } from "../api/types";

function todayISO(offsetDays = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

const FORMAT_ICON = {
  pdf: <FileText size={16} className="text-red-600" />,
  docx: <FileType2 size={16} className="text-sky-700" />,
  xlsx: <FileSpreadsheet size={16} className="text-emerald-600" />,
};

export function ReportsPage() {
  const { can } = useAuth();
  const { data, isLoading, error } = useReports();
  const generate = useGenerateReport();
  const [title, setTitle] = useState("Reporte operacional semanal");
  const [kind, setKind] = useState("operational");
  const [format, setFormat] = useState<"pdf" | "docx" | "xlsx">("pdf");
  const [from, setFrom] = useState(todayISO(-7));
  const [to, setTo] = useState(todayISO());
  const [failure, setFailure] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFailure(null);
    try {
      await generate.mutateAsync({
        title,
        kind,
        format,
        period_start: from,
        period_end: to,
        filters: {},
      });
    } catch (err) {
      setFailure(apiErrorMessage(err));
    }
  }

  async function handleDownload(report: Report) {
    setDownloading(report.id);
    try {
      await downloadReport(report);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-extrabold text-[#343C6A] tracking-tight">Centro de Reportes</h1>
        <p className="text-xs font-medium text-[#718EBF] mt-0.5">
          Reportes operacionales y de gestión con integridad verificable mediante firma criptográfica SHA-256.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-3">
        {can("reports:generate") && (
          <Card title="Generar Nuevo Reporte" subtitle="Seleccione el alcance, fechas y formato deseado" className="xl:col-span-1">
            <form onSubmit={onSubmit} className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Título del Reporte</span>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                  minLength={5}
                  className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Tipo</span>
                  <select
                    value={kind}
                    onChange={(event) => setKind(event.target.value)}
                    className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                  >
                    <option value="operational">Operacional</option>
                    <option value="management">Gestión</option>
                    <option value="executive">Ejecutivo</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Formato</span>
                  <select
                    value={format}
                    onChange={(event) => setFormat(event.target.value as "pdf" | "docx" | "xlsx")}
                    className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2.5 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                  >
                    <option value="pdf">PDF (Ejecutivo)</option>
                    <option value="docx">Word (.docx)</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                  </select>
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Desde</span>
                  <input
                    type="date"
                    value={from}
                    onChange={(event) => setFrom(event.target.value)}
                    className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">Hasta</span>
                  <input
                    type="date"
                    value={to}
                    onChange={(event) => setTo(event.target.value)}
                    className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-3.5 py-2 text-xs font-semibold text-[#343C6A] outline-none focus:border-[#2D60FF] focus:bg-white transition"
                  />
                </label>
              </div>

              {failure && <ErrorNote message={failure} />}

              <Button type="submit" disabled={generate.isPending} className="w-full py-3 text-xs font-bold">
                <Plus size={16} /> {generate.isPending ? "Compilando reporte…" : "Generar Reporte Oficial"}
              </Button>
              {generate.data && (
                <div className="rounded-2xl bg-[#E7FAF8] border border-[#B7F4EE] p-3 text-xs font-bold text-[#16DBCC]">
                  Reporte {generate.data.code} generado con éxito ({generate.data.format.toUpperCase()}).
                </div>
              )}
            </form>
          </Card>
        )}

        <Card title="Historial de Reportes" subtitle="Documentos generados y firmados" className="xl:col-span-2">
          {error && <ErrorNote message={apiErrorMessage(error)} />}
          {isLoading ? (
            <Spinner />
          ) : !data || data.length === 0 ? (
            <EmptyState title="Aún no hay reportes generados" hint="Genere el primero con el formulario de la izquierda." />
          ) : (
            <>
              {/* Vista móvil: tarjetas responsivas estilo BankDash */}
              <div className="divide-y divide-[#F0F5FA] md:hidden">
                {data.map((report) => (
                  <div key={report.id} className="p-4 space-y-2.5 hover:bg-[#F5F7FA]/60 transition">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-[#2D60FF] bg-[#EDF2FF] px-2.5 py-0.5 rounded-full">
                        {report.code}
                      </span>
                      <span className="flex items-center gap-1.5 text-xs font-bold uppercase text-[#343C6A] bg-[#F5F7FA] px-2 py-0.5 rounded-full border border-[#DFEAF2]">
                        {FORMAT_ICON[report.format]} {report.format}
                      </span>
                    </div>

                    <p className="font-bold text-[#343C6A] text-sm leading-snug">{report.title}</p>

                    <div className="flex items-center justify-between text-xs text-[#718EBF]">
                      <span className="capitalize font-semibold">{report.kind} · {fmtBytes(report.file_size)}</span>
                      <span>{fmtDate(report.period_start)} — {fmtDate(report.period_end)}</span>
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <span className="text-[11px] font-medium text-[#718EBF]">{fmtDateTime(report.created_at)}</span>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={report.status !== "completed" || downloading === report.id}
                        onClick={() => void handleDownload(report)}
                        className="text-xs"
                      >
                        <Download size={14} /> Descargar
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Vista escritorio: tabla */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="border-b border-[#F0F5FA] text-left text-xs uppercase font-bold tracking-wider text-[#718EBF]">
                    <tr>
                      <th className="py-3 px-3">Código</th>
                      <th className="py-3 px-3">Reporte</th>
                      <th className="py-3 px-3">Periodo Evaluado</th>
                      <th className="py-3 px-3">Formato</th>
                      <th className="py-3 px-3">Generado</th>
                      <th className="py-3 px-3 text-right" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F0F5FA]">
                    {data.map((report) => (
                      <tr key={report.id} className="hover:bg-[#F5F7FA]/70 transition">
                        <td className="py-3.5 px-3 font-mono text-xs font-bold text-[#2D60FF]">{report.code}</td>
                        <td className="py-3.5 px-3">
                          <p className="font-bold text-[#343C6A]">{report.title}</p>
                          <p className="text-xs font-semibold text-[#718EBF] capitalize">
                            {report.kind} · {fmtBytes(report.file_size)}
                          </p>
                        </td>
                        <td className="py-3.5 px-3 text-xs font-medium text-[#718EBF]">
                          {fmtDate(report.period_start)} — {fmtDate(report.period_end)}
                        </td>
                        <td className="py-3.5 px-3">
                          <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase text-[#343C6A] bg-[#F5F7FA] px-2.5 py-1 rounded-full border border-[#DFEAF2]">
                            {FORMAT_ICON[report.format]} {report.format}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-xs font-medium text-[#718EBF]">{fmtDateTime(report.created_at)}</td>
                        <td className="py-3.5 px-3 text-right">
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={report.status !== "completed" || downloading === report.id}
                            onClick={() => void handleDownload(report)}
                            className="text-xs"
                          >
                            <Download size={14} /> Descargar
                          </Button>
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
    </div>
  );
}

