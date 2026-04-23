import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

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
      await login(pair.access_token, pair.refresh_token);
      navigate("/app/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    }
  };

  return (
    <>
      <h1>Create your MSPintel workspace</h1>
      <form className="stack" onSubmit={onSubmit}>
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          type="password"
        />
        <input value={tenantName} onChange={(e) => setTenantName(e.target.value)} placeholder="Company name" />
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Create account</button>
      </form>
      <p className="version-tag">v{APP_VERSION}</p>
    </>
  );
}
