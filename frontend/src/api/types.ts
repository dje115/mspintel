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
  auth_mode: "tenant" | "platform";
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
export type TenantMspProfile = {
  tenant_id: string;
  legal_name: string | null;
  brand_name: string | null;
  regions_served: string[];
  vertical_focus: string[];
  team_size_band: string | null;
  customer_count_band: string | null;
  typical_customer_size_band: string | null;
  delivery_model: string | null;
  business_goals: string[];
  free_text_description: string | null;
};
export type TenantServiceCatalogEntry = {
  service_key: string;
  service_name: string;
  is_selected: boolean;
  is_custom: boolean;
  sort_order: number;
};
export type TenantServiceCatalog = {
  tenant_id: string;
  items: TenantServiceCatalogEntry[];
};

/** Mirrors ``GET /api/tenant/ai-context`` — same structure wired into AI product context. */
export type TenantAIContext = {
  tenant_id: string;
  msp_profile_summary: {
    legal_name?: string | null;
    brand_name?: string | null;
    delivery_model?: string | null;
    team_size_band?: string | null;
    customer_count_band?: string | null;
    typical_customer_size_band?: string | null;
    free_text_description?: string | null;
  };
  selected_services: string[];
  business_goals: string[];
  vertical_focus: string[];
  regions_served: string[];
  data_confidence_notes: string[];
};

export type SubscriptionResponse = {
  tenant_id: string;
  plan_code: string;
  plan_name: string;
  status: string;
};

export type SourceConnection = {
  id: string;
  system_type: string;
  provider_family: string;
  display_name: string;
  base_url: string | null;
  auth_mode: string;
  status: string;
  is_enabled: boolean;
  health_status: string;
  test_status: string | null;
  test_message: string | null;
  last_error: string | null;
  sync_cadence_minutes: number;
  sync_mode: string;
  connector_version: string;
  connection_metadata: Record<string, unknown> | null;
  safe_config: Record<string, unknown> | null;
  lifecycle_state: string;
  sync_behavior: string;
  is_paused: boolean;
  import_scope_mode: string;
  import_scope_filters: Record<string, unknown> | null;
  last_lifecycle_changed_at: string | null;
  last_lifecycle_note: string | null;
  last_tested_at: string | null;
  last_attempted_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_failed_sync_at: string | null;
  last_sync_at: string | null;
};

export type ConnectorCatalogItem = {
  system_type: string;
  display_name: string;
  description: string;
  system_family: string;
  maturity: "planned" | "stub" | "experimental" | "beta" | "stable";
  supported_auth_modes: string[];
  supports_entities: string[];
  supported_sync_modes: string[];
  implemented: boolean;
  default_cadence_minutes: number;
  connector_version: string;
  ui_help_text?: string | null;
  import_scope_modes: string[];
  import_scope_filter_keys: string[];
  config_fields: {
    key: string;
    label: string;
    required: boolean;
    secret: boolean;
    editable_after_create: boolean;
    help_text?: string | null;
  }[];
};

export type IntegrationSyncRun = {
  id: string;
  source_connection_id: string;
  trigger_mode: string;
  status: string;
  records_processed: number;
  started_at: string | null;
  completed_at: string | null;
  error_summary: string | null;
  sync_cursor: string | null;
  stats_json: Record<string, unknown> | null;
};

export type MappingReviewRow = {
  id: string;
  source_connection_id: string;
  source_connection_name: string | null;
  source_system_key: string | null;
  entity_type: string;
  source_external_id: string;
  source_display_name: string | null;
  source_domain: string | null;
  suggested_customer_id: string | null;
  suggested_customer_name: string | null;
  suggested_confidence: string;
  suggested_score: number | null;
  suggested_reasons: string[];
  status: string;
  status_label: string | null;
  mapped_customer_id: string | null;
  mapped_customer_name: string | null;
  last_sync_run_id: string | null;
  last_sync_status: string | null;
  last_sync_started_at: string | null;
  reviewed_at: string | null;
  notes: string | null;
};

export type IntegrationCoverageItem = {
  source_connection_id: string;
  source_connection_name: string;
  system_type: string;
  lifecycle_state: string;
  import_scope_mode: string;
  linked_customers: number;
  unresolved_mappings: number;
  weak_mappings: number;
};

export type IntegrationCoverageResponse = {
  connected_systems: number;
  unresolved_mappings: number;
  weak_mappings: number;
  phased_onboarding_connections: number;
  items: IntegrationCoverageItem[];
};

export type ExecutiveDashboardResponse = {
  customers: number;
  high_risk_customers: number;
  open_recommendations: number;
  lost_quotes_revisit_count: number;
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

export type RiskQueueRow = {
  customer_id: string;
  customer_name: string;
  owner_name: string | null;
  status: string;
  risk_score: number;
  attention_score: number;
  risk_level: string;
  attention_level: string;
  confidence_level: string;
  reason_codes: string[];
  top_reasons: string[];
  coverage_notes: string[];
  next_step_placeholder: string;
  calculated_at: string;
};

export type RiskQueueResponse = {
  mode: string;
  scoring_version: string;
  page: number;
  page_size: number;
  total: number;
  items: RiskQueueRow[];
};

export type RecommendationRow = {
  id: string;
  customer_id: string | null;
  customer_name: string | null;
  owner_name: string | null;
  scope: string;
  status: string;
  summary: string;
  category: string;
  priority: string;
  suggested_next_action: string;
  created_at: string | null;
};

export type RecommendationListResponse = {
  items: RecommendationRow[];
  page: number;
  page_size: number;
  total: number;
};

export type OpportunityRow = {
  id: string;
  customer_id: string;
  customer_name: string | null;
  title: string;
  status: string;
  value_cents: number | null;
  revisit_reason: string | null;
  suggested_next_action: string;
  created_at: string | null;
};

export type QuoteRow = {
  id: string;
  customer_id: string;
  customer_name: string | null;
  title: string;
  status: string;
  value_cents: number | null;
  revisit_reason: string | null;
  suggested_next_action: string;
  created_at: string | null;
};

export type CommercialHubResponse = {
  opportunities: OpportunityRow[];
  lost_quotes: QuoteRow[];
  open_quotes: QuoteRow[];
};

export type ServiceRiskSection = {
  title: string;
  summary: string;
  metrics: Record<string, number | string>;
  placeholder: boolean;
};

export type ServiceRiskResponse = {
  backup: ServiceRiskSection;
  service_delivery: ServiceRiskSection;
};

export type FinanceCustomerPanel = {
  finance_linked: boolean;
  billing_account_id: string | null;
  display_name: string | null;
  currency_code: string | null;
  snapshot_effective_date: string | null;
  billed_mailboxes: number | null;
  service_active_mailboxes: number | null;
  billed_users: number | null;
  service_licensed_users: number | null;
  payment_status_summary: string | null;
  aged_outstanding_cents: number | null;
  confidence_level: string | null;
  integrity_highlights: string[];
  confidence_notes: string[];
  next_commercial_action_placeholder: string;
  provenance?: Record<string, unknown> | null;
};

export type BillingIntegritySummary = {
  customer_count: number;
  finance_linked_count: number;
  missing_finance_link_count: number;
  orphan_billing_account_count: number;
  underbilling_candidate_count: number;
  overbilling_risk_count: number;
  payment_friction_count: number;
};

export type BillingIntegrityAccountRow = {
  customer_id: string;
  customer_name: string;
  finance_linked: boolean;
  billed_mailboxes: number | null;
  service_mailboxes: number | null;
  billed_users: number | null;
  service_licensed_users: number | null;
  payment_friction: string | null;
  aged_outstanding_cents: number | null;
  confidence_level: string | null;
  signals: string[];
};

export type BillingIntegrityWorkspaceResponse = {
  summary: BillingIntegritySummary;
  coverage_notes: string[];
  accounts: BillingIntegrityAccountRow[];
};

export type M365WorkspaceSummary = {
  customer_count: number;
  linked_count: number;
  connector_configured: boolean;
  connector_health_status: string;
  connector_lifecycle_state: string;
  last_sync_status: string | null;
  last_sync_started_at: string | null;
  last_sync_completed_at: string | null;
  licensed_users_total: number;
  active_users_total: number;
  inactive_users_total: number;
  mailbox_total: number;
  shared_mailbox_total: number;
  stale_users_total: number;
  disabled_users_total: number;
  optimisation_candidate_count: number;
  billing_mismatch_candidate_count: number;
};

export type M365WorkspaceRow = {
  customer_id: string;
  customer_name: string;
  confidence_level: string;
  licensed_users: number | null;
  active_users_30d: number | null;
  inactive_users_30d: number | null;
  disabled_users: number | null;
  stale_users_90d: number | null;
  privileged_admin_users: number | null;
  mailbox_count: number | null;
  shared_mailbox_count: number | null;
  unused_licences: number | null;
  mfa_coverage_pct: number | null;
  tenant_domains: string[];
  entra_summary: Record<string, unknown>;
  azure_summary: Record<string, unknown>;
  billing_impact_signals: string[];
  hygiene_findings: string[];
  optimisation_findings: string[];
  coverage_notes: string[];
};

export type M365WorkspaceResponse = {
  summary: M365WorkspaceSummary;
  coverage_notes: string[];
  customers: M365WorkspaceRow[];
};

export type M365CustomerPanel = {
  linked: boolean;
  confidence_level: string;
  licensed_users: number | null;
  active_users_30d: number | null;
  inactive_users_30d: number | null;
  disabled_users: number | null;
  stale_users_90d: number | null;
  privileged_admin_users: number | null;
  mailbox_count: number | null;
  shared_mailbox_count: number | null;
  unused_licences: number | null;
  mfa_coverage_pct: number | null;
  tenant_domains: string[];
  entra_summary: Record<string, unknown>;
  azure_summary: Record<string, unknown>;
  billing_impact_signals: string[];
  hygiene_findings: string[];
  optimisation_findings: string[];
  confidence_notes: string[];
  next_action_placeholder: string;
};

export type CustomerDetailResponse = {
  id: string;
  name: string;
  status: string;
  owner_name: string | null;
  /** Present on `demo-msp` seeded accounts: synthetic UK MSP scenario JSON for AI/testing. */
  demo_profile?: Record<string, unknown> | null;
  finance?: FinanceCustomerPanel | null;
  m365?: M365CustomerPanel | null;
  connector_coverage?: {
    connected_systems: string[];
    missing_systems: string[];
    unresolved_mapping_count: number;
    confidence_note: string;
  } | null;
  risk_engine?: {
    scoring_version: string;
    calculated_at: string | null;
    risk_level: string;
    attention_level: string;
    confidence_level: string;
    reason_codes: string[];
    factors: Record<string, unknown>[];
    coverage_notes: string[];
  } | null;
  latest_scores: { risk_score: number; attention_score: number; growth_score: number } | null;
  open_tickets_count: number;
  open_opportunities_count: number;
  open_quotes_count: number;
  recommendation_summary: string[];
  recent_actions: string[];
  recommendations: RecommendationRow[];
  opportunities: OpportunityRow[];
  quotes: QuoteRow[];
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

export type PlatformLoginOutcome = "authenticated" | "mfa_challenge" | "mfa_enrollment_setup";

export type PlatformLoginResponse = {
  outcome: PlatformLoginOutcome;
  access_token?: string | null;
  refresh_token?: string | null;
  session_id?: string | null;
  token_type?: string;
  mfa_challenge_token?: string | null;
  enrollment_setup_token?: string | null;
};

export type PlatformMfaStatusResponse = {
  totp_enabled: boolean;
  totp_pending: boolean;
  platform_mfa_required: boolean;
  pending_method_id: string | null;
  recovery_codes_unused: number;
};

export type RecoveryCodesGenerateResponse = {
  codes: string[];
  batch_id: string;
};

export type TotpEnrollmentStartResponse = {
  method_id: string;
  otpauth_uri: string;
};

export type AIProviderSafe = {
  id: string;
  tenant_id: string | null;
  provider_name: string;
  status: string;
  catalog_code: string | null;
  provider_family: string | null;
  deployment_mode: string | null;
  display_label: string | null;
  base_url: string | null;
  has_encrypted_settings: boolean;
  is_enabled: boolean;
};

export type AIProviderTestResult = {
  ok: boolean;
  provider_id: string;
  provider_family: string | null;
  deployment_mode: string | null;
  model_used: string | null;
  message: string;
};

export type TenantAiSettingsResponse = {
  tenant_id: string;
  default_ai_provider: AIProviderSafe | null;
  default_model: string | null;
  fallback_ai_provider: AIProviderSafe | null;
  fallback_model: string | null;
  extra: Record<string, unknown> | null;
};

export type TenantAiTaskRouteRow = {
  id: string;
  task_type: string;
  ai_provider: AIProviderSafe | null;
  model: string | null;
  fallback_ai_provider: AIProviderSafe | null;
  fallback_model: string | null;
  prompt_key: string;
  enabled: boolean;
};

export type PromptListItem = {
  prompt_key: string;
  task_type: string;
  title: string;
  source: "platform" | "tenant_override";
  definition_id: string;
  active_version_id: string | null;
  active_version_number: number | null;
};

export type PromptVersionRow = {
  id: string;
  version_number: number;
  change_note: string | null;
  is_active: boolean;
  created_at: string;
  created_by_user_id: string | null;
  version_metadata: Record<string, unknown> | null;
};

export type PromptDetailResponse = {
  definition_id: string;
  prompt_key: string;
  task_type: string;
  title: string;
  description: string | null;
  scope: string;
  tenant_id: string | null;
  active_version: PromptVersionRow | null;
  versions: PromptVersionRow[];
};

export type ResolvedAITaskResponse = {
  tenant_id: string;
  task_type: string;
  enabled: boolean;
  provider_family: string | null;
  deployment_mode: string | null;
  model: string | null;
  ai_provider_id: string | null;
  prompt_key: string;
  prompt_definition_id: string | null;
  prompt_version_id: string | null;
  prompt_text: string | null;
  fallback_ai_provider_id?: string | null;
  fallback_provider_family?: string | null;
  fallback_deployment_mode?: string | null;
  fallback_model?: string | null;
};

export type AIProductBlockState = {
  status: string;
  text?: string | null;
  message?: string | null;
  run_id?: string | null;
  last_completed_at?: string | null;
  provider_family?: string | null;
  model_used?: string | null;
  prompt_version_id?: string | null;
};

export type AIExecutionOutcome = {
  run_id: string;
  status: string;
  task_type: string;
  text?: string | null;
  message?: string | null;
  provider_family?: string | null;
  deployment_mode?: string | null;
  model_used?: string | null;
  prompt_definition_id?: string | null;
  prompt_version_id?: string | null;
  fallback_used?: boolean;
  duration_ms?: number | null;
  completed_at?: string | null;
};

export type AITaskRunRow = {
  id: string;
  tenant_id: string;
  task_type: string;
  status: string;
  customer_id: string | null;
  recommendation_id: string | null;
  provider_family: string | null;
  deployment_mode: string | null;
  model_used: string | null;
  prompt_definition_id: string | null;
  prompt_version_id: string | null;
  fallback_used: boolean;
  duration_ms: number | null;
  error_summary: string | null;
  output_summary: string | null;
  created_at: string | null;
  completed_at: string | null;
};

export type AIProviderCatalogRow = {
  id: string;
  code: string;
  provider_family: string;
  deployment_mode: string;
  display_name: string;
  description: string | null;
  sort_order: number;
};
