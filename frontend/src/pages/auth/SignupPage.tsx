import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function SignupPage() {
  const navigate = useNavigate();
  const { login } = useSession();

  const [fullName, setFullName] = useState("Jane Founder");
  const [email, setEmail] = useState("jane@example.com");
  const [password, setPassword] = useState("ChangeMe123!");
  const [tenantName, setTenantName] = useState("Acme MSP");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const pair = await api.signup({ full_name: fullName, email, password, tenant_name: tenantName });
      await login(pair.access_token, pair.refresh_token, pair.session_id);
      navigate("/app/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    }
  };

  return (
    <div className="tenant-auth-card tenant-auth-card--wide">
      <div className="tenant-auth-brand">
        <div className="tenant-auth-mark" aria-hidden="true" />
        <div className="tenant-auth-brand-text">
          <strong>mspintel</strong>
          <span>MSP intelligence workspace</span>
        </div>
      </div>

      <p className="tenant-auth-eyebrow">Onboarding</p>
      <h1 className="tenant-auth-title">Create your MSP workspace</h1>
      <p className="tenant-auth-lead">
        You will become the first admin of a new tenant. After signup we will guide you through a short setup checklist
        so your team can start with customers and integrations.
      </p>

      <form className="tenant-form-grid" onSubmit={onSubmit}>
        <label className="tenant-label">
          Company / MSP name
          <input
            className="tenant-input"
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            placeholder="Northwind Managed Services"
          />
        </label>
        <label className="tenant-label">
          Your name
          <input
            className="tenant-input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Alex Rivera"
          />
        </label>
        <label className="tenant-label">
          Work email
          <input
            className="tenant-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@your-msp.com"
            type="email"
            autoComplete="email"
          />
        </label>
        <label className="tenant-label">
          Password
          <input
            className="tenant-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
            type="password"
            autoComplete="new-password"
          />
        </label>
        {error ? <p className="tenant-error">{error}</p> : null}
        <button className="tenant-btn-primary" type="submit">
          Create workspace &amp; continue
        </button>
      </form>

      <p className="tenant-auth-footer">
        Already have a workspace? <Link to="/login">Sign in</Link>
      </p>

      <p className="tenant-version-tag">mspintel v{APP_VERSION}</p>
    </div>
  );
}
