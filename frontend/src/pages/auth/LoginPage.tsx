import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useSession();
  const [email, setEmail] = useState("tenant-admin@demo-msp.example.com");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const pair = await api.login({ email, password });
      await login(pair.access_token, pair.refresh_token, pair.session_id);
      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="tenant-auth-card">
      <div className="tenant-auth-brand">
        <div className="tenant-auth-mark" aria-hidden="true" />
        <div className="tenant-auth-brand-text">
          <strong>mspintel</strong>
          <span>MSP intelligence workspace</span>
        </div>
      </div>

      <p className="tenant-auth-eyebrow">Tenant workspace</p>
      <h1 className="tenant-auth-title">Sign in to your MSP</h1>
      <p className="tenant-auth-lead">
        Access customer health, recommendations, and team tools for the MSP you manage — not the operator console.
      </p>

      <form className="tenant-form-grid" onSubmit={onSubmit}>
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
            placeholder="••••••••"
            type="password"
            autoComplete="current-password"
          />
        </label>
        {error ? <p className="tenant-error">{error}</p> : null}
        <button className="tenant-btn-primary" type="submit">
          Continue to workspace
        </button>
      </form>

      <p className="tenant-auth-footer">
        New MSP workspace? <Link to="/signup">Create an account</Link>
      </p>

      <p className="tenant-auth-platform-link">
        <Link to="/platform/login">Platform operator sign-in →</Link>
      </p>

      <p className="tenant-version-tag">mspintel v{APP_VERSION}</p>
    </div>
  );
}
