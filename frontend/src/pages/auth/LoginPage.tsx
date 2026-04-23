import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

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
      await login(pair.access_token, pair.refresh_token);
      navigate("/app/customers");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <>
      <h1>Login</h1>
      <form className="stack" onSubmit={onSubmit}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          type="password"
        />
        {error ? <p className="error">{error}</p> : null}
        <button type="submit">Sign in</button>
      </form>
      <p className="version-tag">v{APP_VERSION}</p>
    </>
  );
}
