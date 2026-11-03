import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseISO(value);
  return date.toLocaleString("es-PE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  return parseISO(value).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "numeric" });
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "—";
  return formatDistanceToNowStrict(parseISO(value), { addSuffix: true, locale: es });
}

export function fmtNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function fmtMinutes(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return "—";
  if (minutes < 60) return `${fmtNumber(minutes, 1)} min`;
  if (minutes < 1440) return `${fmtNumber(minutes / 60, 1)} h`;
  return `${fmtNumber(minutes / 1440, 1)} d`;
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${fmtNumber(value, digits)}%`;
}

export function fmtBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let index = 0;
  let size = bytes;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(1)} ${units[index]}`;
}
