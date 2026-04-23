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
    <div className="stack">
      <h1>Security & sessions</h1>
      <p className="muted">
        Signed-in devices and browsers. Revoking a session signs that device out on the next refresh.
      </p>

      <div className="row-actions">
        <button type="button" disabled={busy || !refreshToken} onClick={() => void onLogoutOthers()}>
          Sign out other sessions
        </button>
        <button type="button" disabled={busy} onClick={() => void load()}>
          Refresh list
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Current</th>
              <th>Device / agent</th>
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
                  <td className="cell-clip" title={s.user_agent ?? undefined}>
                    {s.device_label || s.user_agent || "Unknown"}
                  </td>
                  <td>{s.ip_address || "—"}</td>
                  <td>{formatTs(s.last_used_at)}</td>
                  <td>{formatTs(s.expires_at)}</td>
                  <td>{active ? "active" : s.revoked_at ? "revoked" : "expired"}</td>
                  <td>
                    {active && !s.is_current ? (
                      <button type="button" disabled={busy} onClick={() => void onRevoke(s.id)}>
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

      <p className="version-tag muted">mspintel v{APP_VERSION}</p>
    </div>
  );
}
