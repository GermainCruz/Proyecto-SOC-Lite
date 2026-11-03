import { useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Bell,
  FileSpreadsheet,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  Search,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Users,
  X,
} from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  permission: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: <LayoutDashboard size={20} />, permission: "dashboard:read" },
  { to: "/alertas", label: "Alertas", icon: <ShieldAlert size={20} />, permission: "alerts:read" },
  { to: "/incidentes", label: "Incidentes", icon: <Siren size={20} />, permission: "incidents:read" },
  { to: "/reportes", label: "Reportes", icon: <FileSpreadsheet size={20} />, permission: "reports:read" },
  { to: "/usuarios", label: "Usuarios y roles", icon: <Users size={20} />, permission: "users:read" },
  { to: "/auditoria", label: "Auditoría", icon: <ScrollText size={20} />, permission: "audit:read" },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Overview",
  "/alertas": "Bandeja de Alertas",
  "/incidentes": "Gestión de Incidentes",
  "/reportes": "Centro de Reportes",
  "/usuarios": "Usuarios y Permisos",
  "/auditoria": "Bitácora de Auditoría",
};

export function Layout() {
  const { user, logout, can } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  const currentTitle = PAGE_TITLES[location.pathname] ?? (location.pathname.startsWith("/alertas/") ? "Detalle de Alerta" : "SOC Operations");
  const items = NAV_ITEMS.filter((item) => can(item.permission));

  return (
    <div className="min-h-screen bg-[#F5F7FA] lg:flex font-sans">
      {/* Fondo oscuro para móvil */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-[#343C6A]/50 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar estilo BankDash: fondo blanco puro, bordes suaves, acento azul real */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 transform border-r border-[#E6EFF5] bg-white transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 flex flex-col justify-between",
          open ? "translate-x-0 shadow-2xl" : "-translate-x-full",
        )}
      >
        <div>
          {/* Logo Brand */}
          <div className="flex h-20 items-center justify-between px-7 border-b border-[#F0F5FA]">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2D60FF] text-white shadow-[0_4px_12px_rgba(45,96,255,0.35)]">
                <Activity size={22} className="stroke-[2.5]" />
              </div>
              <div>
                <p className="text-xl font-extrabold tracking-tight text-[#343C6A]">SOC-Lite</p>
                <p className="text-[10px] uppercase font-bold tracking-wider text-[#718EBF]">SOAR & AI</p>
              </div>
            </div>
            <button
              className="lg:hidden text-[#718EBF] hover:text-[#343C6A]"
              onClick={() => setOpen(false)}
              aria-label="Cerrar menú"
            >
              <X size={20} />
            </button>
          </div>

          {/* Menú de navegación */}
          <nav className="mt-5 space-y-1.5 px-3">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    "group relative flex items-center gap-3.5 rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-150",
                    isActive
                      ? "text-[#2D60FF] bg-[#EDF2FF]/70 font-bold before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1.5 before:bg-[#2D60FF] before:rounded-r-full"
                      : "text-[#718EBF] hover:bg-[#F5F7FA] hover:text-[#2D60FF]",
                  )
                }
              >
                <span className="flex-shrink-0 transition-transform group-hover:scale-110">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Perfil del usuario al pie del sidebar */}
        <div className="border-t border-[#E6EFF5] p-4 bg-white">
          <div className="mb-3 flex items-center gap-3 p-2 rounded-2xl bg-[#F5F7FA]/80">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#2D60FF] to-[#1814F3] text-sm font-bold text-white shadow-sm flex-shrink-0">
              {user?.full_name?.slice(0, 2).toUpperCase() ?? "SO"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-[#343C6A]">{user?.full_name}</p>
              <p className="truncate text-[11px] font-medium text-[#718EBF]">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={() => void logout()}
            className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[#FE5C73] hover:bg-[#FFF0F2] transition"
          >
            <LogOut size={15} /> Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Área principal */}
      <div className="min-w-0 flex-1 flex flex-col">
        {/* Header estilo BankDash: altura 80px, título grande en #343C6A, buscador redondeado, iconos circulares */}
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-[#E6EFF5] bg-white px-6 lg:px-9 backdrop-blur">
          <div className="flex items-center gap-4">
            <button
              className="lg:hidden p-2 rounded-xl text-[#718EBF] hover:bg-[#F5F7FA]"
              onClick={() => setOpen(true)}
              aria-label="Abrir menú"
            >
              <Menu size={22} />
            </button>
            <div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-[#343C6A] tracking-tight">
                {currentTitle}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            {/* Buscador redondeado estilo BankDash */}
            <div className="hidden md:flex items-center gap-2.5 rounded-full bg-[#F5F7FA] px-4 py-2.5 text-xs text-[#718EBF] focus-within:ring-2 focus-within:ring-[#2D60FF]/20">
              <Search size={16} className="text-[#718EBF]" />
              <input
                type="text"
                placeholder="Buscar alerta o activo..."
                className="w-40 lg:w-56 bg-transparent text-xs text-[#343C6A] outline-none placeholder-[#8BA3CB]"
              />
            </div>

            {/* Botón circular Settings */}
            <button
              className="flex h-11 w-11 items-center justify-center rounded-full bg-[#F5F7FA] text-[#718EBF] hover:bg-[#EDF2FF] hover:text-[#2D60FF] transition shadow-xs"
              title="Configuración"
            >
              <Settings size={18} />
            </button>

            {/* Botón circular Notificaciones con punto activo */}
            <button
              className="relative flex h-11 w-11 items-center justify-center rounded-full bg-[#F5F7FA] text-[#FE5C73] hover:bg-[#FFF0F2] transition shadow-xs"
              title="Notificaciones activas"
            >
              <Bell size={18} />
              <span className="absolute top-2.5 right-2.5 h-2 w-2 rounded-full bg-[#FE5C73] ring-2 ring-white" />
            </button>

            {/* Badge de estado en tiempo real */}
            <div className="hidden sm:flex items-center gap-2 rounded-full bg-[#E7FAF8] px-3.5 py-1.5 text-xs font-bold text-[#16DBCC] border border-[#B7F4EE]">
              <span className="h-2 w-2 rounded-full bg-[#16DBCC] animate-pulse" />
              SOC Operativo
            </div>

            {/* Avatar */}
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-tr from-[#2D60FF] to-[#16DBCC] text-xs font-bold text-white shadow-sm ring-2 ring-[#EDF2FF]">
              {user?.full_name?.slice(0, 2).toUpperCase() ?? "SO"}
            </div>
          </div>
        </header>

        {/* Contenido de cada vista */}
        <main className="p-6 lg:p-9 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
