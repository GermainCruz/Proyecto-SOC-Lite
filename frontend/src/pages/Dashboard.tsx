import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Clock,
  Cpu,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";
import { useDashboard } from "../api/queries";
import { Card, KpiCard, Spinner, ErrorNote } from "../components/ui";
import { apiErrorMessage } from "../api/client";
import { fmtMinutes, fmtPct } from "../lib/format";
import type { Severity } from "../api/types";

// Paleta BankDash
const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "#FE5C73", // Coral Pink
  high: "#FEAA09",     // Orange
  medium: "#FFBB38",   // Amber Yellow
  low: "#16DBCC",      // Mint / Cyan
  info: "#2D60FF",     // Electric Blue
};

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Media",
  low: "Baja",
  info: "Info",
};

const SOURCE_COLORS = ["#2D60FF", "#16DBCC", "#FFBB38", "#FE5C73", "#7B61FF"];

export function DashboardPage() {
  const { data, isLoading, error } = useDashboard();

  if (isLoading) return <Spinner label="Cargando panel de operaciones SOC…" />;
  if (error || !data) return <ErrorNote message={apiErrorMessage(error)} />;

  const { kpis } = data;
  const severityTotal = data.by_severity.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="space-y-8">
      {/* Sección Superior: Tarjeta Signature BankDash + Resumen */}
      <div className="grid gap-6 lg:grid-cols-12 items-stretch">
        {/* Tarjeta Signature Azul Eléctrico (Estilo BankDash Credit Card) */}
        <div className="lg:col-span-4 rounded-3xl bg-gradient-to-br from-[#2D60FF] via-[#1E40FF] to-[#1814F3] p-7 text-white shadow-[0_10px_28px_rgba(45,96,255,0.35)] flex flex-col justify-between relative overflow-hidden min-h-[220px]">
          <div className="absolute -right-12 -top-12 w-44 h-44 rounded-full bg-white/10 blur-xl pointer-events-none" />
          <div className="absolute -left-10 -bottom-10 w-36 h-36 rounded-full bg-[#16DBCC]/20 blur-xl pointer-events-none" />

          <div className="relative z-10 flex items-start justify-between">
            <div>
              <span className="text-[11px] uppercase font-bold tracking-widest text-white/75">
                Motor IA Activo
              </span>
              <p className="text-xl font-extrabold tracking-tight mt-0.5">Llama 3.1 Instruct</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-md text-[#16DBCC] border border-white/20">
              <Sparkles size={20} />
            </div>
          </div>

          <div className="relative z-10 my-4">
            <p className="text-xs text-white/70">Confianza Media de Triaje</p>
            <p className="text-3xl font-black text-white tracking-tight mt-0.5">
              {fmtPct(kpis.avg_confidence ? kpis.avg_confidence * 100 : null)}
            </p>
          </div>

          <div className="relative z-10 flex items-center justify-between text-xs text-white/80 pt-3 border-t border-white/15">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="h-2 w-2 rounded-full bg-[#16DBCC] animate-pulse" /> Local Zero-Exfiltration
            </span>
            <span className="font-mono text-[11px] bg-white/15 px-2.5 py-0.5 rounded-full text-white font-semibold">
              Ollama Engine
            </span>
          </div>
        </div>

        {/* Tarjeta Blanca de Acciones Clave y Estado de Operación */}
        <div className="lg:col-span-8 grid gap-4 sm:grid-cols-2">
          <KpiCard
            label="Alertas Abiertas"
            value={String(kpis.open_alerts)}
            hint={`${kpis.alerts_today} nuevas registradas hoy`}
            tone="default"
            icon={<Target size={24} className="stroke-[2.5]" />}
          />
          <KpiCard
            label="Críticas Abiertas"
            value={String(kpis.open_critical)}
            hint="Requieren contención inmediata"
            tone="danger"
            icon={<AlertTriangle size={24} className="stroke-[2.5]" />}
          />
          <KpiCard
            label="MTTT Promedio"
            value={fmtMinutes(kpis.mttt_minutes)}
            hint="Tiempo medio hasta el triaje IA"
            tone="warning"
            icon={<Clock size={24} className="stroke-[2.5]" />}
          />
          <KpiCard
            label="Falsos Positivos"
            value={fmtPct(kpis.fp_rate_pct)}
            hint={`${fmtPct(kpis.auto_triage_pct)} triaje automático`}
            tone="success"
            icon={<ShieldCheck size={24} className="stroke-[2.5]" />}
          />
        </div>
      </div>

      {/* Gráficos Principales: Volumen Diario + Cumplimiento Operativo */}
      <div className="grid gap-6 xl:grid-cols-3">
        <Card
          title="Volumen Diario de Alertas"
          subtitle="Monitoreo de tendencia en los últimos 14 días"
          className="xl:col-span-2"
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_volume} margin={{ top: 12, right: 16, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="bankVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2D60FF" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#2D60FF" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F5FA" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#718EBF" }} stroke="#E6EFF5" />
                <YAxis tick={{ fontSize: 12, fill: "#718EBF" }} stroke="#E6EFF5" allowDecimals={false} />
                <Tooltip
                  formatter={(value) => [`${value} alertas`, "Volumen"]}
                  contentStyle={{
                    borderRadius: 16,
                    borderColor: "#E6EFF5",
                    fontSize: 12,
                    boxShadow: "0 8px 24px rgba(223,230,242,0.6)",
                    color: "#343C6A",
                    fontWeight: 600,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#2D60FF"
                  strokeWidth={3}
                  fill="url(#bankVolume)"
                  name="Alertas"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Cumplimiento Operativo" subtitle="Indicadores clave de rendimiento (KPIs)">
          <dl className="space-y-5">
            <div>
              <div className="flex items-baseline justify-between">
                <dt className="text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                  Cumplimiento SLA Incidentes
                </dt>
                <dd className="text-sm font-extrabold text-[#343C6A]">{fmtPct(data.sla_compliance_pct)}</dd>
              </div>
              <div className="mt-2 h-2.5 rounded-full bg-[#F5F7FA] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#16DBCC] transition-all duration-500"
                  style={{ width: `${Math.min(data.sla_compliance_pct ?? 0, 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-baseline justify-between">
                <dt className="text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                  Tasa de Triaje Automático
                </dt>
                <dd className="text-sm font-extrabold text-[#343C6A]">{fmtPct(kpis.auto_triage_pct)}</dd>
              </div>
              <div className="mt-2 h-2.5 rounded-full bg-[#F5F7FA] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#2D60FF] transition-all duration-500"
                  style={{ width: `${Math.min(kpis.auto_triage_pct ?? 0, 100)}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="rounded-2xl bg-[#F5F7FA] p-3.5 border border-[#E6EFF5]">
                <dt className="text-[11px] font-bold uppercase tracking-wider text-[#718EBF]">MTTR</dt>
                <dd className="mt-1 text-xl font-extrabold text-[#343C6A]">{fmtMinutes(kpis.mttr_minutes)}</dd>
              </div>
              <div className="rounded-2xl bg-[#FFF0F2] p-3.5 border border-[#FFCCD4]">
                <dt className="text-[11px] font-bold uppercase tracking-wider text-[#FE5C73]">SLA Vencidos</dt>
                <dd className="mt-1 text-xl font-extrabold text-[#FE5C73]">{kpis.sla_breached}</dd>
              </div>
            </div>
          </dl>
        </Card>
      </div>

      {/* Distribución por Severidad + Origen + Backlog */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Distribución por Severidad con Barras BankDash */}
        <Card title="Alertas por Severidad" subtitle={`${severityTotal} alertas en los últimos 7 días`}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.by_severity} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F5FA" vertical={false} />
                <XAxis
                  dataKey="severity"
                  tickFormatter={(value) => SEVERITY_LABEL[value as Severity]}
                  tick={{ fontSize: 11, fill: "#718EBF" }}
                  stroke="#E6EFF5"
                />
                <YAxis tick={{ fontSize: 11, fill: "#718EBF" }} stroke="#E6EFF5" allowDecimals={false} />
                <Tooltip
                  formatter={(value) => [`${value} alertas`, "Total"]}
                  labelFormatter={(value) => SEVERITY_LABEL[value as Severity]}
                  contentStyle={{
                    borderRadius: 16,
                    borderColor: "#E6EFF5",
                    fontSize: 12,
                    fontWeight: 600,
                    boxShadow: "0 8px 24px rgba(223,230,242,0.6)",
                  }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                  {data.by_severity.map((item) => (
                    <Cell key={item.severity} fill={SEVERITY_COLORS[item.severity] ?? "#718EBF"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Origen de Alertas - Donut Chart BankDash */}
        <Card title="Origen de Alertas" subtitle="Distribución por sensor / SIEM">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.by_source.filter((item) => item.value > 0)}
                  dataKey="value"
                  nameKey="label"
                  innerRadius={52}
                  outerRadius={82}
                  paddingAngle={3}
                >
                  {data.by_source.map((item, index) => (
                    <Cell key={item.label} fill={SOURCE_COLORS[index % SOURCE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    borderRadius: 16,
                    borderColor: "#E6EFF5",
                    fontSize: 12,
                    fontWeight: 600,
                    boxShadow: "0 8px 24px rgba(223,230,242,0.6)",
                  }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, fontWeight: 600, color: "#718EBF" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Antigüedad del Backlog */}
        <Card title="Backlog de Alertas" subtitle="Antigüedad de eventos pendientes">
          <ul className="space-y-3.5">
            {data.aging_buckets.map((bucket) => {
              const max = Math.max(...data.aging_buckets.map((item) => item.value), 1);
              return (
                <li key={bucket.label}>
                  <div className="flex items-center justify-between text-xs font-bold text-[#718EBF]">
                    <span>{bucket.label}</span>
                    <span className="font-extrabold text-[#343C6A]">{bucket.value}</span>
                  </div>
                  <div className="mt-1.5 h-2 rounded-full bg-[#F5F7FA] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[#2D60FF]"
                      style={{ width: `${(bucket.value / max) * 100}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>

      {/* Top IPs de Origen con Estilo de Lista BankDash */}
      <Card title="Top Direcciones IP de Origen" subtitle="IPs externas con mayor volumen de alertas en los últimos 7 días">
        {data.top_sources_ip.length === 0 ? (
          <p className="text-sm font-medium text-[#718EBF]">Sin datos de origen en el periodo.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.top_sources_ip.map((item, index) => (
              <div
                key={item.label}
                className="flex items-center justify-between p-3.5 rounded-2xl bg-[#F5F7FA] border border-[#E6EFF5] hover:border-[#2D60FF]/30 transition"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-white text-xs font-bold text-[#2D60FF] shadow-xs border border-[#E6EFF5]">
                    {index + 1}
                  </span>
                  <span className="font-mono text-xs font-bold text-[#343C6A]">{item.label}</span>
                </div>
                <span className="text-xs font-extrabold bg-[#EDF2FF] text-[#2D60FF] px-2.5 py-1 rounded-full">
                  {item.value} eventos
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
