import { Navigate, Route, Routes } from "react-router-dom";

import { FallbackNavigate } from "./components/FallbackNavigate";
import { PlatformProtectedRoute } from "./components/PlatformProtectedRoute";
import { TenantProtectedRoute } from "./components/TenantProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
import { PlatformLayout } from "./layout/PlatformLayout";
import { PublicLayout } from "./layout/PublicLayout";
import { SystemStatusPage } from "./pages/admin/SystemStatusPage";
import { AiSettingsPage } from "./pages/app/AiSettingsPage";
import { AtRiskAccountsPage, NeedsAttentionAccountsPage } from "./pages/app/AccountQueuePages";
import { CustomerDetailPage } from "./pages/app/CustomerDetailPage";
import { CustomersPage } from "./pages/app/CustomersPage";
import { DashboardPage } from "./pages/app/DashboardPage";
import { IntegrationsPage } from "./pages/app/IntegrationsPage";
import { IntegrationDetailPage } from "./pages/app/IntegrationDetailPage";
import { MarketingPage } from "./pages/app/MarketingPage";
import { MembersPage } from "./pages/app/MembersPage";
import { OpportunitiesPage } from "./pages/app/OpportunitiesPage";
import { RecommendationsPage } from "./pages/app/RecommendationsPage";
import { ReviewsPage } from "./pages/app/ReviewsPage";
import { SecurityPage } from "./pages/app/SecurityPage";
import { ServiceRiskPage } from "./pages/app/ServiceRiskPage";
import { OnboardingPage } from "./pages/app/OnboardingPage";
import { PromptsPage } from "./pages/app/PromptsPage";
import { DataQualityPage } from "./pages/app/DataQualityPage";
import { AcceptInvitationPage } from "./pages/auth/AcceptInvitationPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { SignupPage } from "./pages/auth/SignupPage";
import { PlatformLoginPage } from "./pages/platform/PlatformLoginPage";
import { PlatformAiProvidersPage } from "./pages/platform/PlatformAiProvidersPage";
import { PlatformAiTaskRunsPage } from "./pages/platform/PlatformAiTaskRunsPage";
import { PlatformOverviewPage } from "./pages/platform/PlatformOverviewPage";
import { PlatformPromptsPage } from "./pages/platform/PlatformPromptsPage";
import { PlatformSecurityPage } from "./pages/platform/PlatformSecurityPage";
import { PlatformSystemStatusPage } from "./pages/platform/PlatformSystemStatusPage";
import { PlatformTenantsPage } from "./pages/platform/PlatformTenantsPage";

function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
      </Route>

      <Route path="/platform/login" element={<PlatformLoginPage />} />

      <Route element={<PlatformProtectedRoute />}>
        <Route path="/platform" element={<PlatformLayout />}>
          <Route index element={<PlatformOverviewPage />} />
          <Route path="tenants" element={<PlatformTenantsPage />} />
          <Route path="system-status" element={<PlatformSystemStatusPage />} />
          <Route path="security" element={<PlatformSecurityPage />} />
          <Route path="ai-providers" element={<PlatformAiProvidersPage />} />
          <Route path="ai-task-runs" element={<PlatformAiTaskRunsPage />} />
          <Route path="prompts" element={<PlatformPromptsPage />} />
        </Route>
      </Route>

      <Route element={<TenantProtectedRoute />}>
        <Route path="/app" element={<AppLayout />}>
          <Route path="recommendations" element={<RecommendationsPage />} />
          <Route path="opportunities" element={<OpportunitiesPage />} />
          <Route path="at-risk" element={<AtRiskAccountsPage />} />
          <Route path="attention" element={<NeedsAttentionAccountsPage />} />
          <Route path="service-risk" element={<ServiceRiskPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="integrations/:id" element={<IntegrationDetailPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="marketing" element={<MarketingPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
          <Route path="data-quality" element={<DataQualityPage />} />
          <Route path="security" element={<SecurityPage />} />
          <Route path="ai-settings" element={<AiSettingsPage />} />
          <Route path="prompts" element={<PromptsPage />} />
          <Route path="system-status" element={<SystemStatusPage />} />
          <Route index element={<DashboardPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<FallbackNavigate />} />
    </Routes>
  );
}

export default App;
