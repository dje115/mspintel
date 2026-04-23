import { NavLink, Outlet } from "react-router-dom";

import { useSession } from "../state/session";

const nav = [
  { to: "/app/customers", label: "Customers" },
  { to: "/app/members", label: "Members" },
  { to: "/app/security", label: "Security" },
  { to: "/app/onboarding", label: "Onboarding" },
  { to: "/app/integrations", label: "Integrations" },
  { to: "/app/system-status", label: "System Status" }
];

export function AppLayout() {
  const { me, currentTenantId, setCurrentTenantId, logout, logoutAll } = useSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <h2>mspintel</h2>
        <nav>
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div>
            <strong>{me?.full_name}</strong>
            <span className="muted"> {me?.email}</span>
            <div className="muted">
              Platform admin: {me?.is_platform_admin ? "yes" : "no"} | Current role: {me?.memberships.find((m) => m.tenant_id === currentTenantId)?.role_code ?? "-"}
            </div>
          </div>

          <div className="topbar-controls">
            <select
              value={currentTenantId ?? ""}
              onChange={(e) => setCurrentTenantId(e.target.value)}
              aria-label="Select tenant"
            >
              {(me?.memberships ?? []).map((m) => (
                <option key={m.tenant_id} value={m.tenant_id}>
                  {m.tenant_name} ({m.role_code})
                </option>
              ))}
            </select>
            <button type="button" onClick={() => void logout()}>
              Logout
            </button>
            <button type="button" onClick={() => void logoutAll()}>
              Logout all
            </button>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
