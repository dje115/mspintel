import { Fragment } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { APP_VERSION } from "../config/version";
import { useSession } from "../state/session";

const navGroups: { title: string; items: { to: string; label: string; end?: boolean }[] }[] = [
  { title: "Overview", items: [{ to: "/app", label: "Dashboard", end: true }] },
  {
    title: "Operations",
    items: [
      { to: "/app/recommendations", label: "Recommendations" },
      { to: "/app/opportunities", label: "Opportunities" },
      { to: "/app/marketing", label: "Marketing & growth" },
      { to: "/app/at-risk", label: "At-risk" },
      { to: "/app/attention", label: "Needs attention" },
      { to: "/app/service-risk", label: "Service risk" },
      { to: "/app/reviews", label: "Review & QBR prep" }
    ]
  },
  { title: "Accounts", items: [{ to: "/app/customers", label: "Accounts & customers" }] },
  {
    title: "Workspace",
    items: [
      { to: "/app/members", label: "Members" },
      { to: "/app/integrations", label: "Integrations" },
      { to: "/app/data-quality", label: "Data quality" },
      { to: "/app/onboarding", label: "Onboarding" },
      { to: "/app/roadmap", label: "Product roadmap" }
    ]
  },
  {
    title: "Administration",
    items: [
      { to: "/app/ai-settings", label: "AI engines" },
      { to: "/app/prompts", label: "Prompts" },
      { to: "/app/security", label: "Security" },
      { to: "/app/system-status", label: "System status" }
    ]
  }
];

export function AppLayout() {
  const { me, currentTenantId, setCurrentTenantId, logout, logoutAll } = useSession();

  return (
    <div className="tenant-shell">
      <aside className="tenant-sidebar">
        <div className="tenant-sidebar-brand">
          <div className="tenant-sidebar-mark" aria-hidden="true" />
          <div>
            <strong>mspintel</strong>
            <span>MSP workspace</span>
          </div>
        </div>

        <nav aria-label="Workspace">
          {navGroups.map((group) => (
            <Fragment key={group.title}>
              <div className="tenant-nav-group">
                <div className="tenant-nav-label">{group.title}</div>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `tenant-nav-link${isActive ? " is-active" : ""}`}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </Fragment>
          ))}
        </nav>

        <div className="tenant-sidebar-foot">Console v{APP_VERSION}</div>
      </aside>

      <div className="tenant-main">
        <header className="tenant-topbar">
          <div className="tenant-topbar-user">
            <strong>{me?.full_name}</strong>
            <span>{me?.email}</span>
            <div className="tenant-topbar-role">
              Role: {me?.memberships.find((m) => m.tenant_id === currentTenantId)?.role_code ?? "—"}
            </div>
          </div>

          <div className="tenant-topbar-actions">
            <select
              className="tenant-select"
              value={currentTenantId ?? ""}
              onChange={(e) => setCurrentTenantId(e.target.value)}
              aria-label="Active tenant"
            >
              {(me?.memberships ?? []).map((m) => (
                <option key={m.tenant_id} value={m.tenant_id}>
                  {m.tenant_name} ({m.role_code})
                </option>
              ))}
            </select>
            <button type="button" className="tenant-btn-ghost" onClick={() => void logout()}>
              Sign out
            </button>
            <button type="button" className="tenant-btn-ghost" onClick={() => void logoutAll()}>
              Sign out everywhere
            </button>
          </div>
        </header>

        <main className="tenant-canvas">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
