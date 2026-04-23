import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { UserSessionRow } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

function formatTs(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function SecurityPage() {
  const { accessToken, currentTenantId, refreshToken, logoutOtherSessions } = useSession();
  const [rows, setRows] = useState<UserSessionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      const data = await api.listSessions(accessToken, currentTenantId);
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    }
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRevoke = async (id: string) => {
    if (!accessToken || !currentTenantId) return;
    setBusy(true);
    setError(null);
    try {
      await api.revokeSession(accessToken, id, currentTenantId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  };

  const onLogoutOthers = async () => {
    setBusy(true);
    setError(null);
    try {
      await logoutOtherSessions();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Security &amp; sessions</h1>
        <p className="tenant-page-sub">
          Devices and browsers signed in to this tenant workspace. Revoking a session signs that device out on the next
          refresh.
        </p>
      </header>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        <button
          type="button"
          className="tenant-btn-primary"
          style={{ width: "auto", minWidth: "auto", padding: "0.5rem 1rem" }}
          disabled={busy || !refreshToken}
          onClick={() => void onLogoutOthers()}
        >
          Sign out other sessions
        </button>
        <button type="button" className="tenant-btn-ghost" disabled={busy} onClick={() => void load()}>
          Refresh list
        </button>
      </div>

      {error ? <p className="tenant-error" style={{ marginBottom: "1rem" }}>{error}</p> : null}

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Active sessions</h2>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Current</th>
                  <th>Device</th>
                  <th>IP</th>
                  <th>Last used</th>
                  <th>Expires</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => {
                  const active = !s.revoked_at && new Date(s.expires_at) > new Date();
                  return (
                    <tr key={s.id}>
                      <td>{s.is_current ? "Yes" : ""}</td>
                      <td className="cell-clip" style={{ maxWidth: "14rem" }} title={s.user_agent ?? undefined}>
                        {s.device_label || s.user_agent || "Unknown"}
                      </td>
                      <td style={{ color: "#64748b" }}>{s.ip_address || "—"}</td>
                      <td style={{ fontSize: "0.86rem" }}>{formatTs(s.last_used_at)}</td>
                      <td style={{ fontSize: "0.86rem" }}>{formatTs(s.expires_at)}</td>
                      <td>{active ? "active" : s.revoked_at ? "revoked" : "expired"}</td>
                      <td>
                        {active && !s.is_current ? (
                          <button type="button" className="tenant-btn-ghost" disabled={busy} onClick={() => void onRevoke(s.id)}>
                            Revoke
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <p className="tenant-version-tag" style={{ marginTop: "1.5rem" }}>
        mspintel v{APP_VERSION}
      </p>
    </div>
  );
}
