import { NavLink, Outlet } from "react-router-dom";

import { APP_VERSION } from "../config/version";
import { useSession } from "../state/session";

const nav = [
  { to: "/platform", label: "Overview", end: true },
  { to: "/platform/tenants", label: "Tenants" },
  { to: "/platform/ai-providers", label: "AI providers" },
  { to: "/platform/connectors", label: "Connectors" },
  { to: "/platform/ai-task-runs", label: "AI runs" },
  { to: "/platform/prompts", label: "Prompts" },
  { to: "/platform/audit", label: "Audit" },
  { to: "/platform/settings", label: "Settings" },
  { to: "/platform/system-status", label: "System status" },
  { to: "/platform/security", label: "Security" }
];

export function PlatformLayout() {
  const { me, logout } = useSession();

  return (
    <div className="platform-shell">
      <aside className="platform-sidebar">
        <div className="platform-brand">
          <span className="platform-brand-mark" aria-hidden="true" />
          <div>
            <strong>MSPintel</strong>
            <div className="platform-brand-sub">Platform console</div>
          </div>
        </div>
        <nav className="platform-nav">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `platform-nav-link${isActive ? " is-active" : ""}`}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <p className="platform-sidebar-version">v{APP_VERSION}</p>
      </aside>

      <div className="platform-main">
        <header className="platform-topbar">
          <div>
            <strong>{me?.full_name}</strong>
            <span className="muted"> {me?.email}</span>
          </div>
          <button type="button" className="platform-text-btn" onClick={() => void logout()}>
            Sign out
          </button>
        </header>
        <main className="platform-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
