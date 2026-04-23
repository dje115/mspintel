import { FormEvent, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

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
    <>
      <h1>Accept invitation</h1>
      <form className="stack" onSubmit={onSubmit}>
        {!accessToken ? (
          <>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name" />
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="Create password"
            />
          </>
        ) : null}
        <button type="submit">Accept invitation</button>
        {message ? <p>{message}</p> : null}
      </form>
      <p className="version-tag">v{APP_VERSION}</p>
    </>
  );
}
