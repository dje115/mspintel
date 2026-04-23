import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function AcceptInvitationPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { accessToken } = useSession();
  const token = useMemo(() => params.get("token") ?? "", [params]);

  const [fullName, setFullName] = useState("New Invited User");
  const [password, setPassword] = useState("ChangeMe123!");
  const [message, setMessage] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.acceptInvitation(
        {
          token,
          ...(accessToken ? {} : { full_name: fullName, password })
        },
        accessToken ?? undefined
      );
      setMessage("Invitation accepted.");
      if (accessToken) {
        navigate("/app/members");
      } else {
        navigate("/login");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to accept invitation");
    }
  };

  return (
    <div className="tenant-auth-card tenant-auth-card--wide">
      <div className="tenant-auth-brand">
        <div className="tenant-auth-mark" aria-hidden="true" />
        <div className="tenant-auth-brand-text">
          <strong>mspintel</strong>
          <span>Join a workspace</span>
        </div>
      </div>

      <p className="tenant-auth-eyebrow">Invitation</p>
      <h1 className="tenant-auth-title">Accept your invite</h1>
      <p className="tenant-auth-lead">
        You are joining an existing MSP workspace. After accepting you can collaborate on accounts, recommendations, and
        service workflows.
      </p>

      <form className="tenant-form-grid" onSubmit={onSubmit}>
        {!accessToken ? (
          <>
            <label className="tenant-label">
              Your name
              <input className="tenant-input" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </label>
            <label className="tenant-label">
              Create password
              <input
                className="tenant-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                autoComplete="new-password"
              />
            </label>
          </>
        ) : null}
        <button className="tenant-btn-primary" type="submit">
          Accept invitation
        </button>
        {message ? (
          <p className={message.startsWith("Invitation") ? "tenant-msg" : "tenant-error"}>{message}</p>
        ) : null}
      </form>

      <p className="tenant-auth-footer">
        Wrong place? <Link to="/login">Tenant sign-in</Link> · <Link to="/platform/login">Operator console</Link>
      </p>

      <p className="tenant-version-tag">mspintel v{APP_VERSION}</p>
    </div>
  );
}
