import { FormEvent, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import type { TotpEnrollmentStartResponse } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";
import { totpSecretFromOtpauthUri } from "../../utils/otpauth";

type Phase = "credentials" | "totp" | "enroll";

export function PlatformLoginPage() {
  const navigate = useNavigate();
  const { login } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("credentials");
  const [mfaChallengeToken, setMfaChallengeToken] = useState<string | null>(null);
  const [enrollmentBearer, setEnrollmentBearer] = useState<string | null>(null);
  const [enrollPayload, setEnrollPayload] = useState<TotpEnrollmentStartResponse | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [enrollTotpCode, setEnrollTotpCode] = useState("");

  const resetMfaState = () => {
    setPhase("credentials");
    setMfaChallengeToken(null);
    setEnrollmentBearer(null);
    setEnrollPayload(null);
    setTotpCode("");
    setEnrollTotpCode("");
    setError(null);
  };

  const finishAuthenticated = async (accessToken: string, refreshToken: string, sessionId?: string) => {
    await login(accessToken, refreshToken, sessionId);
    navigate("/platform");
  };

  const runPasswordStep = async (e?: FormEvent) => {
    e?.preventDefault();
    setError(null);
    try {
      const res = await api.platformLogin({ email, password });
      if (res.outcome === "authenticated") {
        if (!res.access_token || !res.refresh_token) {
          setError("Unexpected response from server.");
          return;
        }
        await finishAuthenticated(res.access_token, res.refresh_token, res.session_id ?? undefined);
        return;
      }
      if (res.outcome === "mfa_challenge") {
        if (!res.mfa_challenge_token) {
          setError("Missing MFA challenge.");
          return;
        }
        setMfaChallengeToken(res.mfa_challenge_token);
        setPhase("totp");
        return;
      }
      if (res.outcome === "mfa_enrollment_setup") {
        if (!res.enrollment_setup_token) {
          setError("Missing enrolment token.");
          return;
        }
        setEnrollmentBearer(res.enrollment_setup_token);
        const start = await api.platformMfaTotpEnrollmentStart(res.enrollment_setup_token);
        setEnrollPayload(start);
        setPhase("enroll");
        return;
      }
      setError("Unable to sign in.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    }
  };

  const onTotpSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!mfaChallengeToken) return;
    setError(null);
    try {
      const pair = await api.platformLoginMfa({ mfa_challenge_token: mfaChallengeToken, totp_code: totpCode.trim() });
      await finishAuthenticated(pair.access_token, pair.refresh_token, pair.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    }
  };

  const onEnrollConfirm = async (e: FormEvent) => {
    e.preventDefault();
    if (!enrollmentBearer || !enrollPayload) return;
    setError(null);
    try {
      await api.platformMfaTotpEnrollmentConfirm(enrollmentBearer, {
        method_id: enrollPayload.method_id,
        totp_code: enrollTotpCode.trim()
      });
      const again = await api.platformLogin({ email, password });
      if (again.outcome !== "mfa_challenge" || !again.mfa_challenge_token) {
        setError("Authenticator enabled but sign-in did not request a code. Try again.");
        return;
      }
      setMfaChallengeToken(again.mfa_challenge_token);
      setEnrollmentBearer(null);
      setEnrollPayload(null);
      setEnrollTotpCode("");
      setPhase("totp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const enrollSecret = enrollPayload ? totpSecretFromOtpauthUri(enrollPayload.otpauth_uri) : null;

  return (
    <div className="platform-public-wrap">
      <div className="platform-login-card">
        <p className="platform-badge">Platform administration</p>
        <h1>MSPintel console</h1>
        <p className="platform-lead">
          Sign in with a platform operator account. Tenant workspaces use the standard tenant login.
        </p>

        {phase === "credentials" ? (
          <form className="stack platform-form" onSubmit={(ev) => void runPasswordStep(ev)}>
            <label className="platform-label">
              Email
              <input
                value={email}
                onChange={(ev) => setEmail(ev.target.value)}
                placeholder="you@company.com"
                type="email"
                autoComplete="username"
              />
            </label>
            <label className="platform-label">
              Password
              <input
                value={password}
                onChange={(ev) => setPassword(ev.target.value)}
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
        ) : null}

        {phase === "totp" ? (
          <div className="stack platform-mfa-panel">
            <p className="platform-mfa-title">Authenticator code</p>
            <p className="muted">Enter the 6-digit code from your authenticator app.</p>
            <form className="stack platform-form" onSubmit={(ev) => void onTotpSubmit(ev)}>
              <label className="platform-label">
                TOTP code
                <input
                  value={totpCode}
                  onChange={(ev) => setTotpCode(ev.target.value)}
                  placeholder="123456"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                />
              </label>
              {error ? <p className="platform-error">{error}</p> : null}
              <button type="submit" className="platform-primary-btn">
                Verify and continue
              </button>
              <button type="button" className="platform-text-btn" onClick={() => resetMfaState()}>
                Back to email and password
              </button>
            </form>
          </div>
        ) : null}

        {phase === "enroll" && enrollPayload ? (
          <div className="stack platform-mfa-panel">
            <p className="platform-mfa-title">Set up authenticator</p>
            <p className="muted">
              Platform policy requires MFA. Scan the QR code (or use the secret), then enter a code to confirm.
            </p>
            <div className="platform-mfa-enroll-grid">
              <div className="platform-mfa-qr">
                <QRCodeSVG value={enrollPayload.otpauth_uri} size={168} level="M" />
              </div>
              <div>
                {enrollSecret ? (
                  <p className="platform-pre platform-mfa-secret" title="Manual entry secret">
                    {enrollSecret}
                  </p>
                ) : null}
                <form className="stack platform-form" onSubmit={(ev) => void onEnrollConfirm(ev)}>
                  <label className="platform-label">
                    Confirmation code
                    <input
                      value={enrollTotpCode}
                      onChange={(ev) => setEnrollTotpCode(ev.target.value)}
                      placeholder="123456"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                    />
                  </label>
                  {error ? <p className="platform-error">{error}</p> : null}
                  <button type="submit" className="platform-primary-btn">
                    Verify and enable
                  </button>
                  <button type="button" className="platform-text-btn" onClick={() => resetMfaState()}>
                    Cancel
                  </button>
                </form>
              </div>
            </div>
          </div>
        ) : null}

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
