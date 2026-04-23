import type {
  CustomerDetailResponse,
  CustomerListResponse,
  ExecutiveDashboardResponse,
  Invitation,
  MeResponse,
  OnboardingResponse,
  PlatformLoginResponse,
  PlatformMfaStatusResponse,
  RecoveryCodesGenerateResponse,
  PlatformOverview,
  PlatformTenantList,
  SourceConnection,
  SubscriptionResponse,
  SystemStatus,
  TenantMember,
  TokenPairResponse,
  TotpEnrollmentStartResponse,
  UserSessionRow
} from "./types";

/**
 * Empty base = same-origin `/api/...` (Vite dev proxy → backend). Set `VITE_API_BASE_URL` only when
 * the UI should call the API host directly (e.g. production build behind its own origin rules).
 */
function apiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (raw === undefined || raw === "") {
    // Dev: same-origin + Vite proxy. Production build: require explicit VITE_API_BASE_URL or default host.
    return import.meta.env.DEV ? "" : "http://localhost:8001";
  }
  return raw.replace(/\/$/, "");
}

const API_BASE = apiBaseUrl();

function authHeaders(accessToken?: string, tenantId?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(tenantId ? { "X-Tenant-Id": tenantId } : {})
  };
}

function formatErrorBody(status: number, body: string): string {
  const trimmed = body.trim();
  if (!trimmed) return `Request failed: ${status}`;
  try {
    const j = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : String(x)))
        .join(", ");
    }
  } catch {
    /* not JSON */
  }
  return trimmed;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(formatErrorBody(res.status, body));
  }
  return (await res.json()) as T;
}

export const api = {
  signup: (payload: { full_name: string; email: string; password: string; tenant_name: string }) =>
    request<TokenPairResponse>("/api/v1/auth/signup", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    }),
  login: (payload: { email: string; password: string }) =>
    request<TokenPairResponse>("/api/v1/auth/login", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    }),
  platformLogin: (payload: { email: string; password: string }) =>
    request<PlatformLoginResponse>("/api/v1/auth/platform/login", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    }),
  platformLoginMfa: (payload: {
    mfa_challenge_token: string;
    totp_code?: string;
    recovery_code?: string;
  }) =>
    request<TokenPairResponse>("/api/v1/auth/platform/login/mfa", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload)
    }),
  platformMfaStatus: (accessToken: string) =>
    request<PlatformMfaStatusResponse>("/api/v1/platform/mfa/status", {
      headers: authHeaders(accessToken)
    }),
  platformMfaTotpEnrollmentStart: (bearer: string) =>
    request<TotpEnrollmentStartResponse>("/api/v1/platform/mfa/totp/enrollment", {
      method: "POST",
      headers: authHeaders(bearer)
    }),
  platformMfaTotpEnrollmentConfirm: (bearer: string, payload: { method_id: string; totp_code: string }) =>
    request<{ status: string }>("/api/v1/platform/mfa/totp/enrollment/confirm", {
      method: "POST",
      headers: authHeaders(bearer),
      body: JSON.stringify(payload)
    }),
  platformMfaTotpDisable: (accessToken: string, payload: { totp_code: string }) =>
    request<{ status: string }>("/api/v1/platform/mfa/totp/disable", {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload)
    }),
  platformMfaRecoveryCodesGenerate: (accessToken: string) =>
    request<RecoveryCodesGenerateResponse>("/api/v1/platform/mfa/recovery-codes/generate", {
      method: "POST",
      headers: authHeaders(accessToken)
    }),
  refresh: (refreshToken: string) =>
    request<TokenPairResponse>("/api/v1/auth/refresh", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ refresh_token: refreshToken })
    }),
  logout: (refreshToken: string) =>
    request<{ status: string }>("/api/v1/auth/logout", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ refresh_token: refreshToken })
    }),
  logoutAll: (accessToken: string, tenantId?: string, body?: { keep_refresh_token?: string }) =>
    request<{ revoked_sessions: number }>("/api/v1/auth/logout-all", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body ?? {})
    }),
  listSessions: (accessToken: string, tenantId?: string) =>
    request<UserSessionRow[]>("/api/v1/auth/sessions", {
      headers: authHeaders(accessToken, tenantId)
    }),
  revokeSession: (accessToken: string, sessionId: string, tenantId?: string) =>
    request<{ revoked: boolean }>(`/api/v1/auth/sessions/${sessionId}/revoke`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  me: (accessToken: string, tenantId?: string) =>
    request<MeResponse>("/api/v1/auth/me", { headers: authHeaders(accessToken, tenantId) }),
  tenantMembers: (accessToken: string, tenantId: string) =>
    request<TenantMember[]>("/api/v1/tenants/current/members", {
      headers: authHeaders(accessToken, tenantId)
    }),
  tenantInvitations: (accessToken: string, tenantId: string) =>
    request<Invitation[]>("/api/v1/tenants/current/invitations", {
      headers: authHeaders(accessToken, tenantId)
    }),
  inviteUser: (accessToken: string, tenantId: string, payload: { email: string; role_to_assign: string }) =>
    request<Invitation>("/api/v1/tenants/current/invitations", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(payload)
    }),
  revokeInvitation: (accessToken: string, tenantId: string, invitationId: string) =>
    request<{ status: string }>(`/api/v1/tenants/current/invitations/${invitationId}/revoke`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  acceptInvitation: (payload: { token: string; full_name?: string; password?: string }, accessToken?: string) =>
    request<{ status: string; tenant_id: string; user_id: string }>("/api/v1/invitations/accept", {
      method: "POST",
      headers: authHeaders(accessToken),
      body: JSON.stringify(payload)
    }),
  currentTenantOnboarding: (accessToken: string, tenantId: string) =>
    request<OnboardingResponse>("/api/v1/tenants/current/onboarding", {
      headers: authHeaders(accessToken, tenantId)
    }),
  updateOnboarding: (accessToken: string, tenantId: string, payload: { status?: string; step?: string }) =>
    request<OnboardingResponse>("/api/v1/tenants/current/onboarding", {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(payload)
    }),
  subscription: (accessToken: string, tenantId: string) =>
    request<SubscriptionResponse>("/api/v1/tenants/current/subscription", {
      headers: authHeaders(accessToken, tenantId)
    }),
  customers: (
    accessToken: string,
    tenantId: string,
    query: { page: number; page_size: number; search?: string; status?: string }
  ) => {
    const qs = new URLSearchParams();
    qs.set("page", String(query.page));
    qs.set("page_size", String(query.page_size));
    if (query.search) qs.set("search", query.search);
    if (query.status) qs.set("status", query.status);
    return request<CustomerListResponse>(`/api/v1/customers?${qs.toString()}`, {
      headers: authHeaders(accessToken, tenantId)
    });
  },
  customerDetail: (accessToken: string, tenantId: string, id: string) =>
    request<CustomerDetailResponse>(`/api/v1/customers/${id}`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  executiveDashboard: (accessToken: string, tenantId: string) =>
    request<ExecutiveDashboardResponse>("/api/v1/dashboards/executive", {
      headers: authHeaders(accessToken, tenantId)
    }),
  systemStatus: (accessToken: string, tenantId: string) =>
    request<SystemStatus>("/api/v1/system/status", { headers: authHeaders(accessToken, tenantId) }),
  integrations: (accessToken: string, tenantId: string) =>
    request<SourceConnection[]>("/api/v1/integrations/connections", {
      headers: authHeaders(accessToken, tenantId)
    }),
  platformOverview: (accessToken: string) =>
    request<PlatformOverview>("/api/v1/platform/overview", { headers: authHeaders(accessToken) }),
  platformTenants: (accessToken: string, query: { page: number; page_size: number }) => {
    const qs = new URLSearchParams();
    qs.set("page", String(query.page));
    qs.set("page_size", String(query.page_size));
    return request<PlatformTenantList>(`/api/v1/platform/tenants?${qs.toString()}`, {
      headers: authHeaders(accessToken)
    });
  },
  platformSystemStatus: (accessToken: string) =>
    request<SystemStatus>("/api/v1/platform/system-status", { headers: authHeaders(accessToken) })
};
