import clsx from "clsx";
import type { ReactNode } from "react";
import type { AlertStatus, Severity, Verdict } from "../api/types";

const severityStyles: Record<Severity, string> = {
  critical: "bg-[#FFF0F2] text-[#FE5C73] border border-[#FFCCD4]",
  high: "bg-[#FFF5D9] text-[#FEAA09] border border-[#FFE8AA]",
  medium: "bg-[#FFF8E7] text-[#FFBB38] border border-[#FFEAB8]",
  low: "bg-[#E7FAF8] text-[#16DBCC] border border-[#B7F4EE]",
  info: "bg-[#EDF2FF] text-[#2D60FF] border border-[#D5E2FF]",
};

const severityLabel: Record<Severity, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Media",
  low: "Baja",
  info: "Info",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider",
        severityStyles[severity] ?? severityStyles.info,
      )}
    >
      {severityLabel[severity] ?? severity}
    </span>
  );
}

const statusLabel: Record<AlertStatus, string> = {
  pending: "Pendiente",
  triaged: "Triada",
  in_review: "En revisión",
  escalated: "Escalada",
  closed: "Cerrada",
  suppressed: "Suprimida",
  false_positive: "Falso positivo",
};

export function StatusBadge({ status }: { status: AlertStatus }) {
  const tone =
    status === "escalated"
      ? "bg-[#FFF0F2] text-[#FE5C73] border border-[#FFCCD4]"
      : status === "false_positive" || status === "closed"
        ? "bg-[#F5F7FA] text-[#718EBF] border border-[#DFEAF2]"
        : status === "triaged"
          ? "bg-[#EDF2FF] text-[#2D60FF] border border-[#D5E2FF]"
          : "bg-[#F3E8FF] text-[#7B61FF] border border-[#E9D5FF]";
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", tone)}>
      {statusLabel[status] ?? status}
    </span>
  );
}

export function VerdictBadge({ verdict, confidence }: { verdict: Verdict; confidence?: number | null }) {
  const map: Record<Verdict, { label: string; tone: string }> = {
    true_positive: { label: "Verdadero positivo", tone: "bg-[#FFF0F2] text-[#FE5C73] border border-[#FFCCD4]" },
    suspicious: { label: "Sospechoso", tone: "bg-[#FFF8E7] text-[#FFBB38] border border-[#FFEAB8]" },
    benign: { label: "Benigno", tone: "bg-[#E7FAF8] text-[#16DBCC] border border-[#B7F4EE]" },
    false_positive: { label: "Falso positivo", tone: "bg-[#F5F7FA] text-[#718EBF] border border-[#DFEAF2]" },
  };
  const item = map[verdict];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold", item.tone)}>
      {item.label}
      {typeof confidence === "number" && (
        <span className="font-mono font-bold opacity-80">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  );
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
  contentClassName,
  noPadding = false,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  noPadding?: boolean;
}) {
  return (
    <section
      className={clsx(
        "rounded-3xl border border-[#E6EFF5] bg-white shadow-[0_4px_24px_rgba(223,230,242,0.45)] flex flex-col overflow-hidden",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-4 border-b border-[#F0F5FA] px-6 sm:px-7 py-4.5 sm:py-5">
          <div className="min-w-0">
            {title && (
              <h2 className="text-base sm:text-lg font-bold text-[#343C6A] tracking-tight">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-1 text-xs font-medium text-[#718EBF]">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
        </header>
      )}
      <div
        className={clsx(
          noPadding ? "" : "p-6 sm:p-7",
          "flex-1 flex flex-col justify-between",
          contentClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  tone = "default",
  icon,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "danger" | "warning" | "success";
  icon?: ReactNode;
}) {
  const iconTones = {
    default: "bg-[#EDF2FF] text-[#2D60FF]",
    danger: "bg-[#FFF0F2] text-[#FE5C73]",
    warning: "bg-[#FFF5D9] text-[#FEAA09]",
    success: "bg-[#E7FAF8] text-[#16DBCC]",
  };

  return (
    <div className="rounded-3xl border border-[#E6EFF5] bg-white p-5 sm:p-6 shadow-[0_4px_20px_rgba(223,230,242,0.45)] hover:shadow-[0_8px_28px_rgba(223,230,242,0.7)] transition-all duration-200">
      <div className="flex items-center gap-4">
        {icon && (
          <div className={clsx("flex h-14 w-14 flex-none items-center justify-center rounded-full", iconTones[tone])}>
            {icon}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wider text-[#718EBF]">{label}</p>
          <p className="mt-1 text-2xl sm:text-3xl font-extrabold text-[#343C6A] tracking-tight">{value}</p>
          {hint && <p className="mt-0.5 text-xs font-medium text-[#718EBF] truncate">{hint}</p>}
        </div>
      </div>
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled,
  type = "button",
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const variants = {
    primary:
      "bg-[#2D60FF] hover:bg-[#1814F3] text-white shadow-[0_4px_14px_rgba(45,96,255,0.3)] disabled:bg-slate-300 disabled:shadow-none",
    secondary:
      "border border-[#DFEAF2] bg-white text-[#343C6A] hover:bg-[#F5F7FA] hover:border-[#2D60FF]/30 shadow-sm",
    ghost: "text-[#718EBF] hover:text-[#2D60FF] hover:bg-[#EDF2FF]",
    danger: "bg-[#FE5C73] hover:bg-[#E0435A] text-white shadow-[0_4px_14px_rgba(254,92,115,0.3)]",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" ? "px-3 py-1.5 text-xs" : "px-5 py-2.5 text-sm",
        variants[variant],
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm font-semibold text-[#718EBF]">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-[#EDF2FF] border-t-[#2D60FF]" />
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="py-14 text-center">
      <p className="text-base font-bold text-[#343C6A]">{title}</p>
      {hint && <p className="mt-1 text-xs font-medium text-[#718EBF]">{hint}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-[#FFCCD4] bg-[#FFF0F2] px-4 py-3 text-sm font-medium text-[#FE5C73]">
      {message}
    </div>
  );
}
