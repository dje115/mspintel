import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function PlatformLoginPage() {
  const navigate = useNavigate();
  const { login } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const pair = await api.platformLogin({ email, password });
      await login(pair.access_token, pair.refresh_token, pair.session_id);
      navigate("/platform");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    }
  };

  return (
    <div className="platform-public-wrap">
      <div className="platform-login-card">
        <p className="platform-badge">Platform administration</p>
        <h1>MSPintel console</h1>
        <p className="platform-lead">Sign in with a platform operator account. Tenant workspaces use the standard tenant login.</p>
        <form className="stack platform-form" onSubmit={onSubmit}>
          <label className="platform-label">
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" type="email" autoComplete="username" />
          </label>
          <label className="platform-label">
            Password
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="platform-error">{error}</p> : null}
          <button type="submit" className="platform-primary-btn">
            Sign in to platform
          </button>
        </form>
        <p className="platform-footer-links">
          <Link to="/login">Tenant login</Link>
          <span aria-hidden="true"> · </span>
          <Link to="/signup">Create tenant workspace</Link>
        </p>
        <p className="platform-version-tag">Console v{APP_VERSION}</p>
      </div>
    </div>
  );
}
