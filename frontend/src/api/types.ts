export type TokenPairResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
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
  user_id: string;
  full_name: string;
  email: string;
  role_code: string;
  status: string;
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
