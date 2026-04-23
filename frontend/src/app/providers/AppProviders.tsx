import type { ReactNode } from "react";

import { AppShellStateProvider } from "../state/appShellState";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <AppShellStateProvider
      value={{
        publicArea: "landing/pricing/signup",
        appArea: "tenant dashboards",
        platformAdminArea: "cross-tenant operations",
        tenantAdminArea: "tenant settings and members",
        onboardingArea: "tenant onboarding flow",
        tenantSwitcherArea: "user tenant switch UX"
      }}
    >
      {children}
    </AppShellStateProvider>
  );
}
