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
    <div className="stack">
      <h1>Tenant members</h1>
      <div className="table-wrap">
        <table>
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
              <tr key={m.user_id}>
                <td>{m.full_name}</td>
                <td>{m.email}</td>
                <td>{m.role_code}</td>
                <td>{m.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Pending invitations</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Expires</th>
              <th>Accept URL</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {invites.map((i) => (
              <tr key={i.id}>
                <td>{i.email}</td>
                <td>{i.role_to_assign}</td>
                <td>{i.status}</td>
                <td>{new Date(i.expires_at).toLocaleString()}</td>
                <td className="accept-url-cell">{i.accept_url}</td>
                <td>
                  {i.status === "pending" && canManage ? (
                    <button onClick={() => onRevoke(i.id)}>Revoke</button>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canManage ? (
        <form className="stack" onSubmit={onInvite}>
          <h2>Invite user</h2>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            type="email"
            required
          />
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="tenant_admin">Tenant Admin</option>
            <option value="director">Director</option>
            <option value="sales_user">Sales User</option>
            <option value="account_manager">Account Manager</option>
            <option value="service_manager">Service Manager</option>
            <option value="marketing_user">Marketing User</option>
          </select>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit">Send Invitation</button>
        </form>
      ) : null}
    </div>
  );
}
