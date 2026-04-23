import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./layout/AppLayout";
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

function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
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

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;
