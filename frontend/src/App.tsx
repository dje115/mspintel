import { Navigate, Route, Routes } from "react-router-dom";

import { FallbackNavigate } from "./components/FallbackNavigate";
import { PlatformProtectedRoute } from "./components/PlatformProtectedRoute";
import { TenantProtectedRoute } from "./components/TenantProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
import { PlatformLayout } from "./layout/PlatformLayout";
import { PublicLayout } from "./layout/PublicLayout";
import { SystemStatusPage } from "./pages/admin/SystemStatusPage";
import { CustomerDetailPage } from "./pages/app/CustomerDetailPage";
import { CustomersPage } from "./pages/app/CustomersPage";
import { IntegrationsPage } from "./pages/app/IntegrationsPage";
import { MembersPage } from "./pages/app/MembersPage";
import { SecurityPage } from "./pages/app/SecurityPage";
import { OnboardingPage } from "./pages/app/OnboardingPage";
import { AcceptInvitationPage } from "./pages/auth/AcceptInvitationPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { SignupPage } from "./pages/auth/SignupPage";
import { PlatformLoginPage } from "./pages/platform/PlatformLoginPage";
import { PlatformOverviewPage } from "./pages/platform/PlatformOverviewPage";
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
        </Route>
      </Route>

      <Route element={<TenantProtectedRoute />}>
        <Route path="/app" element={<AppLayout />}>
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="security" element={<SecurityPage />} />
          <Route path="system-status" element={<SystemStatusPage />} />
          <Route index element={<Navigate to="customers" replace />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<FallbackNavigate />} />
    </Routes>
  );
}

export default App;
