import type {
  AIExecutionOutcome,
  ConnectorCatalogItem,
  IntegrationCoverageResponse,
  AIProductBlockState,
  AIProviderSafe,
  AIProviderTestResult,
  AIProviderCatalogRow,
  AITaskRunRow,
  BillingIntegrityWorkspaceResponse,
  M365WorkspaceResponse,
  CommercialHubResponse,
  IntegrationSyncRun,
  MappingReviewRow,
  MappingCreateCustomersResponse,
  CustomerDetailResponse,
  CustomerListResponse,
  CustomerReviewArtifactListResponse,
  CustomerReviewArtifactOut,
  CustomerReviewLatestArtifactsResponse,
  ReviewAiGenerationResponse,
  ReviewWorkspaceContextResponse,
  ExecutiveDashboardResponse,
  Invitation,
  MeResponse,
  OnboardingResponse,
  PlatformLoginResponse,
  PlatformMfaStatusResponse,
  PromptDetailResponse,
  PromptListItem,
  RecoveryCodesGenerateResponse,
  PlatformOverview,
  PlatformTenantList,
  RecommendationListResponse,
  RecommendationRow,
  RiskQueueResponse,
  ResolvedAITaskResponse,
  ServiceRiskResponse,
  SourceConnection,
  SubscriptionResponse,
  TenantMspProfile,
  TenantAIContext,
  TenantServiceCatalog,
  SystemStatus,
  TenantAiSettingsResponse,
  TenantAiTaskRouteRow,
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
  tenantProfile: (accessToken: string, tenantId: string) =>
    request<TenantMspProfile>("/api/tenant/profile", { headers: authHeaders(accessToken, tenantId) }),
  updateTenantProfile: (accessToken: string, tenantId: string, payload: Omit<TenantMspProfile, "tenant_id">) =>
    request<TenantMspProfile>("/api/tenant/profile", {
      method: "PUT",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(payload)
    }),
  tenantServiceCatalogue: (accessToken: string, tenantId: string) =>
    request<TenantServiceCatalog>("/api/tenant/service-catalogue", { headers: authHeaders(accessToken, tenantId) }),
  updateTenantServiceCatalogue: (accessToken: string, tenantId: string, payload: TenantServiceCatalog) =>
    request<TenantServiceCatalog>("/api/tenant/service-catalogue", {
      method: "PUT",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(payload)
    }),
  tenantAiContext: (accessToken: string, tenantId: string) =>
    request<TenantAIContext>("/api/tenant/ai-context", { headers: authHeaders(accessToken, tenantId) }),
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
  workspaceRecommendations: (
    accessToken: string,
    tenantId: string,
    query: {
      page: number;
      page_size: number;
      status?: string;
      scope?: string;
      customer_id?: string;
      owner?: string;
    }
  ) => {
    const qs = new URLSearchParams();
    qs.set("page", String(query.page));
    qs.set("page_size", String(query.page_size));
    if (query.status) qs.set("status", query.status);
    if (query.scope) qs.set("scope", query.scope);
    if (query.customer_id) qs.set("customer_id", query.customer_id);
    if (query.owner) qs.set("owner", query.owner);
    return request<RecommendationListResponse>(`/api/v1/workspace/recommendations?${qs.toString()}`, {
      headers: authHeaders(accessToken, tenantId)
    });
  },
  patchRecommendation: (accessToken: string, tenantId: string, id: string, status: string) =>
    request<RecommendationRow>(`/api/v1/workspace/recommendations/${id}`, {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify({ status })
    }),
  workspaceCommercial: (accessToken: string, tenantId: string) =>
    request<CommercialHubResponse>("/api/v1/workspace/commercial", {
      headers: authHeaders(accessToken, tenantId)
    }),
  billingIntegrityWorkspace: (accessToken: string, tenantId: string) =>
    request<BillingIntegrityWorkspaceResponse>("/api/v1/workspace/billing-integrity", {
      headers: authHeaders(accessToken, tenantId)
    }),
  m365HealthWorkspace: (accessToken: string, tenantId: string) =>
    request<M365WorkspaceResponse>("/api/v1/workspace/m365-health", {
      headers: authHeaders(accessToken, tenantId)
    }),
  getM365HealthAiSummary: (accessToken: string, tenantId: string) =>
    request<AIProductBlockState>("/api/v1/workspace/m365-health/ai/latest", {
      headers: authHeaders(accessToken, tenantId)
    }),
  postM365HealthAiSummary: (accessToken: string, tenantId: string) =>
    request<AIExecutionOutcome>("/api/v1/workspace/m365-health/ai/summary", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getM365HealthAiOpportunity: (accessToken: string, tenantId: string) =>
    request<AIProductBlockState>("/api/v1/workspace/m365-health/ai/opportunity/latest", {
      headers: authHeaders(accessToken, tenantId)
    }),
  postM365HealthAiOpportunity: (accessToken: string, tenantId: string) =>
    request<AIExecutionOutcome>("/api/v1/workspace/m365-health/ai/opportunity", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  riskQueue: (
    accessToken: string,
    tenantId: string,
    query: { mode: "at_risk" | "attention"; page: number; page_size: number; search?: string; owner?: string }
  ) => {
    const qs = new URLSearchParams();
    qs.set("mode", query.mode);
    qs.set("page", String(query.page));
    qs.set("page_size", String(query.page_size));
    if (query.search) qs.set("search", query.search);
    if (query.owner) qs.set("owner", query.owner);
    return request<RiskQueueResponse>(`/api/v1/workspace/risk-queue?${qs.toString()}`, {
      headers: authHeaders(accessToken, tenantId)
    });
  },
  recomputeRiskEngine: (accessToken: string, tenantId: string, customerId?: string) =>
    request<{ mode: string; scoring_version: string; processed: number }>(
      `/api/v1/workspace/risk-engine/recompute${customerId ? `?customer_id=${encodeURIComponent(customerId)}` : ""}`,
      {
        method: "POST",
        headers: authHeaders(accessToken, tenantId)
      }
    ),
  workspaceServiceRisk: (accessToken: string, tenantId: string) =>
    request<ServiceRiskResponse>("/api/v1/workspace/service-risk", {
      headers: authHeaders(accessToken, tenantId)
    }),
  systemStatus: (accessToken: string, tenantId: string) =>
    request<SystemStatus>("/api/v1/system/status", { headers: authHeaders(accessToken, tenantId) }),
  integrations: (accessToken: string, tenantId: string) =>
    request<SourceConnection[]>("/api/v1/integrations/connections", {
      headers: authHeaders(accessToken, tenantId)
    }),
  integrationCatalog: (accessToken: string, tenantId: string) =>
    request<ConnectorCatalogItem[]>("/api/v1/integrations/catalog", {
      headers: authHeaders(accessToken, tenantId)
    }),
  createIntegrationConnection: (
    accessToken: string,
    tenantId: string,
    body: {
      system_type: string;
      display_name: string;
      base_url?: string | null;
      auth_mode?: string;
      is_enabled?: boolean;
      sync_cadence_minutes?: number;
      config?: Record<string, unknown>;
    }
  ) =>
    request<SourceConnection>("/api/v1/integrations/connections", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  updateIntegrationConnection: (
    accessToken: string,
    tenantId: string,
    connectionId: string,
    body: {
      system_type: string;
      display_name: string;
      base_url?: string | null;
      auth_mode?: string;
      is_enabled?: boolean;
      sync_cadence_minutes?: number;
      config?: Record<string, unknown>;
    }
  ) =>
    request<SourceConnection>(`/api/v1/integrations/connections/${connectionId}`, {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  testIntegrationConnection: (accessToken: string, tenantId: string, connectionId: string) =>
    request<SourceConnection>(`/api/v1/integrations/connections/${connectionId}/test`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  syncIntegrationConnection: (accessToken: string, tenantId: string, connectionId: string) =>
    request<IntegrationSyncRun>(`/api/v1/integrations/connections/${connectionId}/sync`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  integrationRuns: (accessToken: string, tenantId: string, connectionId: string, limit = 20) =>
    request<IntegrationSyncRun[]>(`/api/v1/integrations/connections/${connectionId}/runs?limit=${limit}`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  updateIntegrationLifecycle: (
    accessToken: string,
    tenantId: string,
    connectionId: string,
    body: { lifecycle_state?: string; is_enabled?: boolean; is_paused?: boolean; sync_behavior?: string; note?: string }
  ) =>
    request<SourceConnection>(`/api/v1/integrations/connections/${connectionId}/lifecycle`, {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  updateIntegrationImportScope: (
    accessToken: string,
    tenantId: string,
    connectionId: string,
    body: { import_scope_mode: string; filters?: Record<string, unknown> }
  ) =>
    request<SourceConnection>(`/api/v1/integrations/connections/${connectionId}/import-scope`, {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  integrationCoverage: (accessToken: string, tenantId: string) =>
    request<IntegrationCoverageResponse>("/api/v1/integrations/coverage", {
      headers: authHeaders(accessToken, tenantId)
    }),
  integrationMappings: (
    accessToken: string,
    tenantId: string,
    query?: {
      connection_id?: string;
      status_filter?: string;
      confidence?: string;
      search?: string;
      customer_id?: string;
    }
  ) => {
    const qs = new URLSearchParams();
    if (query?.connection_id) qs.set("connection_id", query.connection_id);
    if (query?.status_filter) qs.set("status_filter", query.status_filter);
    if (query?.confidence) qs.set("confidence", query.confidence);
    if (query?.search) qs.set("search", query.search);
    if (query?.customer_id) qs.set("customer_id", query.customer_id);
    const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
    return request<MappingReviewRow[]>(`/api/v1/integrations/mappings${suffix}`, {
      headers: authHeaders(accessToken, tenantId)
    });
  },
  integrationMappingAction: (
    accessToken: string,
    tenantId: string,
    reviewId: string,
    body: { action: string; customer_id?: string; notes?: string }
  ) =>
    request<MappingReviewRow>(`/api/v1/integrations/mappings/${reviewId}/action`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  integrationCreateCustomersFromMappings: (
    accessToken: string,
    tenantId: string,
    body: { review_ids?: string[]; connection_id?: string }
  ) =>
    request<MappingCreateCustomersResponse>("/api/v1/integrations/mappings/create-customers", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
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
    request<SystemStatus>("/api/v1/platform/system-status", { headers: authHeaders(accessToken) }),
  getAiSettings: (accessToken: string, tenantId: string) =>
    request<TenantAiSettingsResponse>("/api/v1/ai/settings", { headers: authHeaders(accessToken, tenantId) }),
  patchAiSettings: (accessToken: string, tenantId: string, body: Record<string, unknown>) =>
    request<TenantAiSettingsResponse>("/api/v1/ai/settings", {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  getAiTaskRoutes: (accessToken: string, tenantId: string) =>
    request<TenantAiTaskRouteRow[]>("/api/v1/ai/task-routes", { headers: authHeaders(accessToken, tenantId) }),
  patchAiTaskRoutes: (accessToken: string, tenantId: string, body: { routes: Record<string, unknown>[] }) =>
    request<TenantAiTaskRouteRow[]>("/api/v1/ai/task-routes", {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  listAiProviders: (accessToken: string, tenantId: string) =>
    request<AIProviderSafe[]>("/api/v1/ai/providers", { headers: authHeaders(accessToken, tenantId) }),
  createAiProvider: (
    accessToken: string,
    tenantId: string,
    body: {
      catalog_code?: string | null;
      provider_family: string;
      deployment_mode: string;
      display_label?: string | null;
      base_url?: string | null;
      settings?: Record<string, unknown> | null;
    }
  ) =>
    request<AIProviderSafe>("/api/v1/ai/providers", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  patchAiProvider: (
    accessToken: string,
    tenantId: string,
    providerId: string,
    body: {
      display_label?: string | null;
      base_url?: string | null;
      provider_name?: string | null;
      is_enabled?: boolean;
      settings?: Record<string, unknown> | null;
    }
  ) =>
    request<AIProviderSafe>(`/api/v1/ai/providers/${providerId}`, {
      method: "PATCH",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  deleteAiProvider: (accessToken: string, tenantId: string, providerId: string) =>
    fetch(`${API_BASE}/api/v1/ai/providers/${providerId}`, {
      method: "DELETE",
      headers: authHeaders(accessToken, tenantId)
    }).then(async (res) => {
      if (!res.ok) {
        const body = await res.text();
        throw new Error(formatErrorBody(res.status, body));
      }
    }),
  testAiProvider: (accessToken: string, tenantId: string, providerId: string) =>
    request<AIProviderTestResult>(`/api/v1/ai/providers/${providerId}/test`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  resolveAiTask: (accessToken: string, tenantId: string, taskType: string) =>
    request<ResolvedAITaskResponse>(`/api/v1/ai/resolve/${encodeURIComponent(taskType)}`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  listPrompts: (accessToken: string, tenantId: string) =>
    request<PromptListItem[]>("/api/v1/prompts", { headers: authHeaders(accessToken, tenantId) }),
  getPromptDetail: (accessToken: string, tenantId: string, definitionId: string) =>
    request<PromptDetailResponse>(`/api/v1/prompts/${definitionId}`, { headers: authHeaders(accessToken, tenantId) }),
  addPromptVersion: (
    accessToken: string,
    tenantId: string,
    definitionId: string,
    body: { prompt_text: string; change_note?: string | null }
  ) =>
    request<PromptDetailResponse>(`/api/v1/prompts/${definitionId}/versions`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  activatePromptVersion: (accessToken: string, tenantId: string, definitionId: string, versionId: string) =>
    request<PromptDetailResponse>(`/api/v1/prompts/${definitionId}/activate/${versionId}`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  revertPromptToDefault: (accessToken: string, tenantId: string, promptKey: string) =>
    request<{ status: string }>("/api/v1/prompts/revert-to-default", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify({ prompt_key: promptKey })
    }),
  createTenantPromptOverride: (
    accessToken: string,
    tenantId: string,
    body: {
      prompt_key: string;
      title: string;
      task_type: string;
      initial_version: { prompt_text: string; change_note?: string | null };
    }
  ) =>
    request<PromptDetailResponse>("/api/v1/prompts/tenant-overrides", {
      method: "POST",
      headers: authHeaders(accessToken, tenantId),
      body: JSON.stringify(body)
    }),
  platformAiProviderCatalog: (accessToken: string) =>
    request<AIProviderCatalogRow[]>("/api/v1/platform/ai/providers/catalog", { headers: authHeaders(accessToken) }),
  platformListPrompts: (accessToken: string) =>
    request<PromptDetailResponse[]>("/api/v1/platform/prompts", { headers: authHeaders(accessToken) }),
  platformAiTaskRuns: (accessToken: string, limit = 80) =>
    request<AITaskRunRow[]>(`/api/v1/platform/ai/task-runs?limit=${limit}`, { headers: authHeaders(accessToken) }),
  getCustomerAccountSummaryAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/account-summary`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postCustomerAccountSummaryAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/account-summary`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getCustomerRiskSummaryAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/risk-summary`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postCustomerRiskSummaryAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/risk-summary`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getCustomerChurnExplanationAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/churn-explanation`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postCustomerChurnExplanationAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/churn-explanation`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getCustomerReviewAgendaAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/customer-review-agenda`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postCustomerReviewAgendaAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/customer-review-agenda`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getAccountManagerNextConversationAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/account-manager-next-conversation`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postAccountManagerNextConversationAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/account-manager-next-conversation`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getAccountManagerCallScriptAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIProductBlockState>(`/api/v1/customers/${customerId}/ai/account-manager-call-script`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postAccountManagerCallScriptAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<AIExecutionOutcome>(`/api/v1/customers/${customerId}/ai/account-manager-call-script`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  getRecommendationExplanationAi: (accessToken: string, tenantId: string, recommendationId: string) =>
    request<AIProductBlockState>(`/api/v1/workspace/recommendations/${recommendationId}/ai/explanation`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postRecommendationExplanationAi: (accessToken: string, tenantId: string, recommendationId: string) =>
    request<AIExecutionOutcome>(`/api/v1/workspace/recommendations/${recommendationId}/ai/explanation`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  reviewWorkspaceContext: (accessToken: string, tenantId: string, customerId: string) =>
    request<ReviewWorkspaceContextResponse>(`/api/v1/reviews/${customerId}/context`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  reviewArtifactsList: (
    accessToken: string,
    tenantId: string,
    customerId: string,
    opts?: { artifact_type?: string; limit?: number }
  ) => {
    const q = new URLSearchParams();
    if (opts?.artifact_type) q.set("artifact_type", opts.artifact_type);
    if (opts?.limit != null) q.set("limit", String(opts.limit));
    const qs = q.toString();
    return request<CustomerReviewArtifactListResponse>(
      `/api/v1/reviews/${customerId}/ai/artifacts${qs ? `?${qs}` : ""}`,
      { headers: authHeaders(accessToken, tenantId) }
    );
  },
  reviewArtifactsLatest: (accessToken: string, tenantId: string, customerId: string) =>
    request<CustomerReviewLatestArtifactsResponse>(`/api/v1/reviews/${customerId}/ai/artifacts/latest`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  reviewArtifactGet: (accessToken: string, tenantId: string, customerId: string, artifactId: string) =>
    request<CustomerReviewArtifactOut>(`/api/v1/reviews/${customerId}/ai/artifacts/${artifactId}`, {
      headers: authHeaders(accessToken, tenantId)
    }),
  postReviewAgendaAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<ReviewAiGenerationResponse>(`/api/v1/reviews/${customerId}/ai/agenda`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  postReviewAccountNotesAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<ReviewAiGenerationResponse>(`/api/v1/reviews/${customerId}/ai/account-notes`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  postReviewCallScriptAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<ReviewAiGenerationResponse>(`/api/v1/reviews/${customerId}/ai/call-script`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    }),
  postReviewEmailDraftAi: (accessToken: string, tenantId: string, customerId: string, opts?: { tone?: string | null }) => {
    const q = new URLSearchParams();
    if (opts?.tone) q.set("tone", opts.tone);
    const qs = q.toString();
    return request<ReviewAiGenerationResponse>(`/api/v1/reviews/${customerId}/ai/email-draft${qs ? `?${qs}` : ""}`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    });
  },
  postReviewCustomerReportAi: (accessToken: string, tenantId: string, customerId: string) =>
    request<ReviewAiGenerationResponse>(`/api/v1/reviews/${customerId}/ai/customer-report`, {
      method: "POST",
      headers: authHeaders(accessToken, tenantId)
    })
};
