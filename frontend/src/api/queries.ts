import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  AlertDetail,
  AlertPage,
  AuditPage,
  Dashboard,
  Incident,
  OrgUser,
  Report,
  Severity,
  Triage,
} from "./types";

export const qk = {
  dashboard: ["dashboard"] as const,
  alerts: (params: AlertFilters | Record<string, unknown>) => ["alerts", params] as const,
  alert: (id: string) => ["alert", id] as const,
  incidents: (params: Record<string, unknown>) => ["incidents", params] as const,
  users: ["users"] as const,
  audit: (params: Record<string, unknown>) => ["audit", params] as const,
  reports: ["reports"] as const,
};

export interface AlertFilters {
  [key: string]: unknown;
  severity?: Severity | "";
  status?: string;
  source?: string;
  q?: string;
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  sort?: string;
}

export function useDashboard() {
  return useQuery({
    queryKey: qk.dashboard,
    queryFn: async () => (await api.get<Dashboard>("/dashboard")).data,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useAlerts(filters: AlertFilters) {
  return useQuery({
    queryKey: qk.alerts(filters),
    queryFn: async () => {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, value]) => value !== "" && value !== undefined && value !== null),
      );
      return (await api.get<AlertPage>("/alerts", { params })).data;
    },
    placeholderData: (previous) => previous,
  });
}

export function useAlert(id: string | undefined) {
  return useQuery({
    queryKey: qk.alert(id ?? ""),
    queryFn: async () => (await api.get<AlertDetail>(`/alerts/${id}`)).data,
    enabled: Boolean(id),
  });
}

export function useUpdateAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      (await api.patch(`/alerts/${id}`, payload)).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: qk.alert(variables.id) });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
    },
  });
}

export function useRunTriage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, force = false }: { id: string; force?: boolean }) =>
      (await api.post<Triage>(`/alerts/${id}/triage`, null, { params: { force } })).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: qk.alert(variables.id) });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

export function useReviewTriage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, verdict, comment }: { id: string; verdict: string; comment: string }) =>
      (await api.post(`/alerts/${id}/review`, { verdict, comment })).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: qk.alert(variables.id) });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

export function useEscalateAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.post<{ incident_id: string; code: string }>(`/alerts/${id}/escalate`)).data,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: qk.alert(id) });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useIncidents(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: qk.incidents(params),
    queryFn: async () => (await api.get<Incident[]>("/incidents", { params })).data,
    refetchInterval: 120_000,
  });
}

export function useUpdateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      (await api.patch(`/incidents/${id}`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["incidents"] }),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: qk.users,
    queryFn: async () => (await api.get<OrgUser[]>("/users")).data,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await api.post("/users", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.users }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      (await api.patch(`/users/${id}`, payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.users }),
  });
}

export function useAudit(params: Record<string, unknown>) {
  return useQuery({
    queryKey: qk.audit(params),
    queryFn: async () => (await api.get<AuditPage>("/audit", { params })).data,
    placeholderData: (previous) => previous,
  });
}

export function useVerifyChain() {
  return useMutation({
    mutationFn: async () => (await api.get("/audit/verify")).data,
  });
}

export function useReports() {
  return useQuery({
    queryKey: qk.reports,
    queryFn: async () => (await api.get<Report[]>("/reports")).data,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await api.post<Report>("/reports", payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.reports }),
  });
}

export async function downloadReport(report: Report) {
  const response = await api.get(`/reports/${report.id}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(response.data as Blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${report.code}_${report.kind}.${report.format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
