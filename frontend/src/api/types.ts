export type TokenPairResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  session_id: string;
};

export type MembershipSummary = {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role_code: string;
};

export type MeResponse = {
  user_id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
  auth_mode: "tenant" | "platform";
  memberships: MembershipSummary[];
};

export type Invitation = {
  id: string;
  email: string;
  role_to_assign: string;
  status: string;
  accept_url: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
  debug_token?: string | null;
};

export type TenantMember = {
  membership_id: string;
  user_id: string;
  full_name: string;
  email: string;
  role_code: string;
  status: string;
};

export type UserSessionRow = {
  id: string;
  ip_address: string | null;
  device_label: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  revoked_at: string | null;
  is_current: boolean;
};

export type OnboardingResponse = { tenant_id: string; status: string; step: string };
export type SubscriptionResponse = {
  tenant_id: string;
  plan_code: string;
  plan_name: string;
  status: string;
};

export type SourceConnection = {
  id: string;
  system_type: string;
  display_name: string;
  status: string;
  last_sync_at: string | null;
};

export type CustomerListItem = {
  id: string;
  name: string;
  status: string;
  owner_name: string | null;
  risk_score: number | null;
  attention_score: number | null;
  growth_score: number | null;
  next_best_action: string | null;
};

export type CustomerListResponse = {
  items: CustomerListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type CustomerDetailResponse = {
  id: string;
  name: string;
  status: string;
  owner_name: string | null;
  latest_scores: { risk_score: number; attention_score: number; growth_score: number } | null;
  open_tickets_count: number;
  open_opportunities_count: number;
  open_quotes_count: number;
  recommendation_summary: string[];
  recent_actions: string[];
};

export type SystemStatus = {
  api: string;
  environment: string;
  version: string;
  db: string;
  redis: string;
  tenant_count: number;
  user_count: number;
  source_connection_count: number;
};

export type PlatformOverview = {
  tenant_count: number;
  user_count: number;
  subscription_count: number;
  app_version: string;
  environment: string;
};

export type PlatformTenantRow = {
  tenant_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  onboarding_status: string | null;
  onboarding_step: string | null;
  subscription_status: string | null;
  plan_code: string | null;
  plan_name: string | null;
};

export type PlatformTenantList = {
  items: PlatformTenantRow[];
  page: number;
  page_size: number;
  total: number;
};
