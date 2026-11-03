import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { Activity, Check, LockKeyhole, ShieldCheck, Sparkles, UserCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiErrorMessage } from "../api/client";
import { Button, ErrorNote } from "../components/ui";

interface DemoAccount {
  name: string;
  role: string;
  email: string;
  badge: string;
  badgeColor: string;
  avatarBg: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    name: "María Quispe",
    role: "Analista SOC",
    email: "analista1@soclite.local",
    badge: "Triaje y Operación",
    badgeColor: "bg-[#EDF2FF] text-[#2D60FF] border-[#D5E2FF]",
    avatarBg: "bg-[#2D60FF] text-white",
  },
  {
    name: "Carla Mendoza",
    role: "Auditor",
    email: "auditor@soclite.local",
    badge: "Cadena SHA-256",
    badgeColor: "bg-[#E7FAF8] text-[#16DBCC] border-[#B7F4EE]",
    avatarBg: "bg-[#16DBCC] text-white",
  },
  {
    name: "Ana Torres",
    role: "Administrador",
    email: "admin@soclite.local",
    badge: "Control Total / RBAC",
    badgeColor: "bg-[#FFF0F2] text-[#FE5C73] border-[#FFCCD4]",
    avatarBg: "bg-[#FE5C73] text-white",
  },
  {
    name: "Luis Paredes",
    role: "Jefe de SOC",
    email: "gerente.soc@soclite.local",
    badge: "SLAs y Reportes",
    badgeColor: "bg-[#FFF5D9] text-[#FEAA09] border-[#FFE8AA]",
    avatarBg: "bg-[#FEAA09] text-white",
  },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("analista1@soclite.local");
  const [password, setPassword] = useState("SocLite#2026!");
  const [selectedEmail, setSelectedEmail] = useState("analista1@soclite.local");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function handleSelectAccount(acc: DemoAccount) {
    setEmail(acc.email);
    setPassword("SocLite#2026!");
    setSelectedEmail(acc.email);
    setError(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-[#F5F7FA] lg:grid-cols-12">
      {/* Panel Izquierdo Hero - Paleta Corporativa Deep Navy / Slate (Sobrio y Profesional) */}
      <section className="hidden lg:col-span-5 lg:flex flex-col justify-between bg-gradient-to-br from-[#1A233A] via-[#151C2E] to-[#0E1322] p-12 text-white shadow-2xl relative overflow-hidden border-r border-[#1E293B]">
        {/* Decoraciones de fondo suaves, sin estridencias ni tonos fosforescentes */}
        <div className="absolute -right-20 -top-20 w-80 h-80 rounded-full bg-[#2D60FF]/15 blur-3xl pointer-events-none" />
        <div className="absolute -left-20 -bottom-20 w-80 h-80 rounded-full bg-[#1814F3]/15 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#2D60FF] shadow-lg shadow-[#2D60FF]/25 text-white">
            <Activity size={24} className="stroke-[2.5]" />
          </div>
          <div>
            <p className="text-xl font-extrabold tracking-tight text-white">SOC-Lite</p>
            <p className="text-[10px] uppercase tracking-[0.25em] text-slate-400 font-semibold">
              Plataforma de Operaciones SOC
            </p>
          </div>
        </div>

        <div className="relative z-10 max-w-md my-auto">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-1 text-xs font-medium backdrop-blur-md mb-6 text-slate-200 border border-white/10">
            <Sparkles size={14} className="text-[#5078FF]" /> Triaje Cognitivo con Llama 3.1
          </div>

          <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-white">
            Menos ruido.
            <span className="block text-[#5078FF]">Mayor señal operativa.</span>
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-300">
            Automatización inteligente de triaje, respuesta a incidentes con trazabilidad inmutable y
            diseño inspirado en analítica de alto desempeño.
          </p>

          <div className="mt-8 space-y-3.5">
            {[
              "Triaje asistido por IA local (sin exfiltración de logs)",
              "Deduplicación automática y mitigación de ruido",
              "Bitácora inmutable verificable con SHA-256",
            ].map((feature, i) => (
              <div key={i} className="flex items-center gap-3 text-sm text-slate-200">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#2D60FF]/20 text-[#5078FF] border border-[#2D60FF]/30">
                  <Check size={13} className="stroke-[3]" />
                </span>
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs text-slate-400">
          © 2026 SOC-Lite Platform · Entorno Seguro de Demostración
        </p>
      </section>

      {/* Panel Derecho - Formulario y Selector de Cuentas */}
      <section className="col-span-12 lg:col-span-7 flex items-center justify-center p-6 sm:p-10 lg:p-16">
        <div className="w-full max-w-lg bg-white rounded-3xl p-8 sm:p-10 shadow-[0_4px_30px_rgba(223,230,242,0.6)] border border-[#E6EFF5]">
          {/* Logo en versión móvil */}
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2D60FF] text-white">
              <Activity size={22} />
            </div>
            <div>
              <p className="text-xl font-extrabold text-[#343C6A]">SOC-Lite</p>
              <p className="text-[10px] uppercase tracking-wider text-[#718EBF]">Triaje automático</p>
            </div>
          </div>

          <div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#343C6A]">Iniciar Sesión</h2>
            <p className="mt-1.5 text-sm text-[#718EBF]">
              Selecciona una cuenta de prueba para autocompletar tus credenciales.
            </p>
          </div>

          {/* Selector de Cuentas Demo para Prueba (Autocompletado) */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-[#718EBF] flex items-center gap-1.5">
                <UserCheck size={14} className="text-[#2D60FF]" /> Cuentas para Selección Rápida
              </span>
              <span className="text-[11px] text-[#2D60FF] font-semibold bg-[#EDF2FF] px-2 py-0.5 rounded-full">
                Clic para autocompletar
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_ACCOUNTS.map((acc) => {
                const isSelected = selectedEmail === acc.email;
                return (
                  <button
                    key={acc.email}
                    type="button"
                    onClick={() => handleSelectAccount(acc)}
                    className={`group text-left p-3 rounded-2xl border transition-all duration-200 relative ${
                      isSelected
                        ? "border-[#2D60FF] bg-[#EDF2FF]/60 shadow-[0_2px_12px_rgba(45,96,255,0.15)] ring-2 ring-[#2D60FF]/20"
                        : "border-[#E6EFF5] bg-[#F5F7FA]/70 hover:bg-white hover:border-[#2D60FF]/40 hover:shadow-sm"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-xl text-xs font-bold transition ${acc.avatarBg}`}
                      >
                        {acc.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold text-[#343C6A] truncate group-hover:text-[#2D60FF]">
                          {acc.name}
                        </p>
                        <p className="text-[11px] font-medium text-[#718EBF] truncate">{acc.role}</p>
                      </div>
                      {isSelected && (
                        <span className="h-5 w-5 rounded-full bg-[#2D60FF] text-white flex items-center justify-center flex-shrink-0">
                          <Check size={12} className="stroke-[3]" />
                        </span>
                      )}
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${acc.badgeColor}`}
                      >
                        {acc.badge}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Formulario */}
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                Correo Electrónico
              </label>
              <input
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setSelectedEmail(event.target.value);
                }}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-3 text-sm text-[#343C6A] font-medium focus:border-[#2D60FF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#2D60FF]/15 transition"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-[#718EBF]">
                  Contraseña
                </label>
                <span className="text-[11px] text-[#718EBF]">Común: SocLite#2026!</span>
              </div>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-2xl border border-[#DFEAF2] bg-[#F5F7FA] px-4 py-3 text-sm text-[#343C6A] font-medium focus:border-[#2D60FF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#2D60FF]/15 transition"
              />
            </div>

            {error && <ErrorNote message={error} />}

            <Button
              type="submit"
              disabled={busy}
              className="w-full py-3.5 text-base font-bold bg-[#2D60FF] hover:bg-[#1814F3] text-white rounded-2xl shadow-[0_6px_20px_rgba(45,96,255,0.35)] active:scale-[0.99] transition"
            >
              <LockKeyhole size={18} />
              {busy ? "Iniciando sesión…" : "Entrar a SOC-Lite"}
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
