import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { Invitation, TenantMember } from "../../api/types";
import { useSession } from "../../state/session";

export function MembersPage() {
  const { accessToken, currentTenantId, me } = useSession();
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("sales_user");
  const [error, setError] = useState<string | null>(null);

  const canManage =
    me?.is_platform_admin ||
    (me?.memberships.find((m) => m.tenant_id === currentTenantId)?.role_code === "tenant_admin");

  const refresh = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    const [membersData, inviteData] = await Promise.all([
      api.tenantMembers(accessToken, currentTenantId),
      api.tenantInvitations(accessToken, currentTenantId)
    ]);
    setMembers(membersData);
    setInvites(inviteData);
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onInvite = async (e: FormEvent) => {
    e.preventDefault();
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      await api.inviteUser(accessToken, currentTenantId, { email, role_to_assign: role });
      setEmail("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to invite user");
    }
  };

  const onRevoke = async (id: string) => {
    if (!accessToken || !currentTenantId) return;
    await api.revokeInvitation(accessToken, currentTenantId, id);
    await refresh();
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Team &amp; invites</h1>
        <p className="tenant-page-sub">
          People who can access this MSP workspace. Tenant admins can invite colleagues and assign roles aligned to your
          delivery model.
        </p>
      </header>

      <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Members</h2>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.membership_id}>
                    <td>{m.full_name}</td>
                    <td style={{ color: "#64748b" }}>{m.email}</td>
                    <td>
                      <span className="tenant-badge tenant-badge--muted">{m.role_code}</span>
                    </td>
                    <td>{m.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="tenant-panel" style={{ marginBottom: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Pending invitations</h2>
        </div>
        <div className="tenant-panel-body">
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Expires</th>
                  <th>Accept link</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {invites.map((i) => (
                  <tr key={i.id}>
                    <td>{i.email}</td>
                    <td>{i.role_to_assign}</td>
                    <td>{i.status}</td>
                    <td style={{ color: "#64748b", fontSize: "0.86rem" }}>{new Date(i.expires_at).toLocaleString()}</td>
                    <td className="accept-url-cell" style={{ maxWidth: "12rem", fontSize: "0.8rem" }}>
                      {i.accept_url}
                    </td>
                    <td>
                      {i.status === "pending" && canManage ? (
                        <button type="button" className="tenant-btn-ghost" onClick={() => void onRevoke(i.id)}>
                          Revoke
                        </button>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {canManage ? (
        <section className="tenant-panel">
          <div className="tenant-panel-head">
            <h2 className="tenant-panel-title">Invite a teammate</h2>
          </div>
          <div className="tenant-panel-body" style={{ padding: "1.1rem 1.25rem" }}>
            <form className="tenant-form-grid" style={{ maxWidth: "28rem" }} onSubmit={onInvite}>
              <label className="tenant-label">
                Email
                <input
                  className="tenant-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  type="email"
                  required
                />
              </label>
              <label className="tenant-label">
                Role
                <select className="tenant-select" style={{ width: "100%" }} value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="tenant_admin">Tenant Admin</option>
                  <option value="director">Director</option>
                  <option value="sales_user">Sales User</option>
                  <option value="account_manager">Account Manager</option>
                  <option value="service_manager">Service Manager</option>
                  <option value="marketing_user">Marketing User</option>
                </select>
              </label>
              {error ? <p className="tenant-error">{error}</p> : null}
              <button className="tenant-btn-primary" type="submit" style={{ width: "auto", minWidth: "10rem" }}>
                Send invitation
              </button>
            </form>
          </div>
        </section>
      ) : null}
    </div>
  );
}
