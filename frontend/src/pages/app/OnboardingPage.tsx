import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

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
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Workspace onboarding</h1>
        <p className="tenant-page-sub">
          Complete these steps so your MSP gets the most from customer intelligence, integrations, and team access.
        </p>
      </header>

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Progress</h2>
          <Link className="tenant-panel-link" to="/app">
            Go to dashboard
          </Link>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1.25rem 1.35rem" }}>
          {!data ? (
            <div className="tenant-skeleton">Loading onboarding state…</div>
          ) : (
            <ul className="tenant-list-plain" style={{ paddingLeft: "1.25rem" }}>
              <li>
                <strong>Status:</strong> {data.status}
              </li>
              <li>
                <strong>Current step:</strong> {data.step}
              </li>
              <li>Connect PSA / RMM under Integrations when connectors are enabled.</li>
              <li>Invite your delivery and sales leads from Team &amp; invites.</li>
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
