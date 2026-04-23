import { createContext, useContext } from "react";

type AppShellState = {
  publicArea: string;
  appArea: string;
  platformAdminArea: string;
  tenantAdminArea: string;
  onboardingArea: string;
  tenantSwitcherArea: string;
};

const AppShellStateContext = createContext<AppShellState>({
  publicArea: "",
  appArea: "",
  platformAdminArea: "",
  tenantAdminArea: "",
  onboardingArea: "",
  tenantSwitcherArea: ""
});

export const AppShellStateProvider = AppShellStateContext.Provider;

export function useAppShellState(): AppShellState {
  return useContext(AppShellStateContext);
}
