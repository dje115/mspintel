import type {
  CustomerDetailResponse,
  CustomerListResponse,
  Invitation,
  MeResponse,
  OnboardingResponse,
  SourceConnection,
  SubscriptionResponse,
  SystemStatus,
  TenantMember,
  TokenPairResponse,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
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
  logoutAll: (accessToken: string, tenantId: string, body?: { keep_refresh_token?: string }) =>
    request<{ revoked_sessions: number }>("/api/v1/auth/logout-all", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body ?? {})
    }),
  listSessions: (accessToken: string, tenantId: string) =>
    request<UserSessionRow[]>("/api/v1/auth/sessions", {
      headers: authHeaders(accessToken, tenantId)
    }),
  revokeSession: (accessToken: string, tenantId: string, sessionId: string) =>
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
    request<{ customers: number; high_risk_customers: number; open_recommendations: number; lost_quotes_revisit_count: number }>(
      "/api/v1/dashboards/executive",
      { headers: authHeaders(accessToken, tenantId) }
    ),
  systemStatus: (accessToken: string, tenantId: string) =>
    request<SystemStatus>("/api/v1/system/status", { headers: authHeaders(accessToken, tenantId) }),
  integrations: (accessToken: string, tenantId: string) =>
    request<SourceConnection[]>("/api/v1/integrations/connections", {
      headers: authHeaders(accessToken, tenantId)
    })
};
