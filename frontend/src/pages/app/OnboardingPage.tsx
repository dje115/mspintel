import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { useSession } from "../../state/session";

export function OnboardingPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<{ status: string; step: string } | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api.currentTenantOnboarding(accessToken, currentTenantId).then(setData);
  }, [accessToken, currentTenantId]);

  return (
    <div className="stack">
      <h1>Onboarding</h1>
      <p>Tenant created and ready for setup.</p>
      <p>Current status: {data?.status ?? "loading"}</p>
      <p>Current step: {data?.step ?? "loading"}</p>
      <p>Next: connect source systems and confirm subscription details.</p>
    </div>
  );
}
