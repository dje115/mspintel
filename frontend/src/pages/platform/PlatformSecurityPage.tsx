import { FormEvent, useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import { api } from "../../api/client";
import type { PlatformMfaStatusResponse, TotpEnrollmentStartResponse, UserSessionRow } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";
import { totpSecretFromOtpauthUri } from "../../utils/otpauth";

function formatTs(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function PlatformSecurityPage() {
  const { accessToken, refreshToken, logoutOtherSessions } = useSession();
  const [rows, setRows] = useState<UserSessionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mfaStatus, setMfaStatus] = useState<PlatformMfaStatusResponse | null>(null);
  const [mfaBusy, setMfaBusy] = useState(false);
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [enrollDraft, setEnrollDraft] = useState<TotpEnrollmentStartResponse | null>(null);
  const [enrollCode, setEnrollCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [recoveryReveal, setRecoveryReveal] = useState<string[] | null>(null);

  const loadSessions = useCallback(async () => {
    if (!accessToken) return;
    setError(null);
    try {
      const data = await api.listSessions(accessToken);
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    }
  }, [accessToken]);

  const loadMfa = useCallback(async () => {
    if (!accessToken) return;
    setMfaError(null);
    try {
      const s = await api.platformMfaStatus(accessToken);
      setMfaStatus(s);
    } catch (e) {
      setMfaError(e instanceof Error ? e.message : "Failed to load MFA status");
    }
  }, [accessToken]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    void loadMfa();
  }, [loadMfa]);

  const onRevoke = async (id: string) => {
    if (!accessToken) return;
    setBusy(true);
    setError(null);
    try {
      await api.revokeSession(accessToken, id);
      await loadSessions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  };

  const onLogoutOthers = async () => {
    setBusy(true);
    setError(null);
    try {
      await logoutOtherSessions();
      await loadSessions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  const onStartEnroll = async () => {
    if (!accessToken) return;
    setMfaBusy(true);
    setMfaError(null);
    setEnrollCode("");
    try {
      const start = await api.platformMfaTotpEnrollmentStart(accessToken);
      setEnrollDraft(start);
    } catch (e) {
      setMfaError(e instanceof Error ? e.message : "Could not start enrolment");
    } finally {
      setMfaBusy(false);
    }
  };

  const onConfirmEnroll = async (e: FormEvent) => {
    e.preventDefault();
    if (!accessToken || !enrollDraft) return;
    setMfaBusy(true);
    setMfaError(null);
    try {
      await api.platformMfaTotpEnrollmentConfirm(accessToken, {
        method_id: enrollDraft.method_id,
        totp_code: enrollCode.trim()
      });
      setEnrollDraft(null);
      setEnrollCode("");
      await loadMfa();
    } catch (e) {
      setMfaError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setMfaBusy(false);
    }
  };

  const onDisable = async (e: FormEvent) => {
    e.preventDefault();
    if (!accessToken) return;
    if (!window.confirm("Disable platform authenticator? You will need to enrol again if policy requires MFA.")) {
      return;
    }
    setMfaBusy(true);
    setMfaError(null);
    try {
      await api.platformMfaTotpDisable(accessToken, { totp_code: disableCode.trim() });
      setDisableCode("");
      await loadMfa();
    } catch (e) {
      setMfaError(e instanceof Error ? e.message : "Disable failed");
    } finally {
      setMfaBusy(false);
    }
  };

  const enrollSecret = enrollDraft ? totpSecretFromOtpauthUri(enrollDraft.otpauth_uri) : null;

  return (
    <div className="stack platform-page platform-security-page">
      <div>
        <h1>Platform security</h1>
        <p className="muted">
          Platform-console refresh sessions only. Shorter-lived tokens than tenant workspaces; revoke a row to sign
          that device out on the next refresh.
        </p>
        <p className="version-tag">Console v{APP_VERSION}</p>
      </div>

      <section className="card platform-policy-card">
        <h2>Authenticator (TOTP)</h2>
        {mfaStatus ? (
          <ul className="platform-policy-list">
            <li>
              Status:{" "}
              <strong>{mfaStatus.totp_enabled ? "enabled" : mfaStatus.totp_pending ? "pending" : "not set up"}</strong>
            </li>
            <li>Policy: platform MFA required = {mfaStatus.platform_mfa_required ? "yes" : "no"}</li>
            <li>
              Recovery codes (unused): <strong>{mfaStatus.recovery_codes_unused ?? 0}</strong>
            </li>
          </ul>
        ) : (
          <p className="muted">Loading MFA status…</p>
        )}
        {mfaError ? <p className="error">{mfaError}</p> : null}

        {!mfaStatus?.totp_enabled ? (
          <div className="stack platform-mfa-admin">
            {!enrollDraft ? (
              <button type="button" className="platform-primary-btn" disabled={mfaBusy || !accessToken} onClick={() => void onStartEnroll()}>
                Start authenticator enrolment
              </button>
            ) : (
              <div className="platform-mfa-enroll-grid">
                <div className="platform-mfa-qr">
                  <QRCodeSVG value={enrollDraft.otpauth_uri} size={160} level="M" />
                </div>
                <div>
                  {enrollSecret ? (
                    <p className="platform-pre platform-mfa-secret" title="Manual entry secret">
                      {enrollSecret}
                    </p>
                  ) : null}
                  <form className="stack platform-form" onSubmit={(ev) => void onConfirmEnroll(ev)}>
                    <label className="platform-label">
                      Confirm with 6-digit code
                      <input
                        value={enrollCode}
                        onChange={(ev) => setEnrollCode(ev.target.value)}
                        placeholder="123456"
                        inputMode="numeric"
                      />
                    </label>
                    <button type="submit" className="platform-primary-btn" disabled={mfaBusy}>
                      Verify and enable
                    </button>
                    <button type="button" className="platform-text-btn" disabled={mfaBusy} onClick={() => setEnrollDraft(null)}>
                      Cancel
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        ) : (
          <form className="stack platform-form platform-mfa-disable" onSubmit={(ev) => void onDisable(ev)}>
            <label className="platform-label">
              Disable — enter current authenticator code
              <input
                value={disableCode}
                onChange={(ev) => setDisableCode(ev.target.value)}
                placeholder="123456"
                inputMode="numeric"
              />
            </label>
            <button type="submit" className="platform-text-btn" disabled={mfaBusy}>
              Disable authenticator
            </button>
          </form>
        )}
      </section>

      {mfaStatus?.totp_enabled ? (
        <section className="card platform-policy-card">
          <h2>Recovery codes</h2>
          <p className="muted">
            One-time backup codes if you lose your authenticator device. Each code works once. Store them offline
            (password manager or print). The server only keeps hashes — you will <strong>never</strong> see these codes
            again after this screen.
          </p>
          {recoveryReveal ? (
            <div className="platform-recovery-reveal stack">
              <p className="platform-error">Copy now. This list will disappear when you leave the page.</p>
              <ul className="platform-recovery-list">
                {recoveryReveal.map((c) => (
                  <li key={c}>
                    <code>{c}</code>
                  </li>
                ))}
              </ul>
              <button type="button" className="platform-text-btn" onClick={() => setRecoveryReveal(null)}>
                Dismiss
              </button>
            </div>
          ) : null}
          <div className="row-actions">
            <button
              type="button"
              className="platform-primary-btn"
              disabled={mfaBusy || !accessToken}
              onClick={() => {
                if (
                  !window.confirm(
                    "Generate a new set of recovery codes? Any unused previous codes will stop working. Continue?"
                  )
                ) {
                  return;
                }
                void (async () => {
                  if (!accessToken) return;
                  setMfaBusy(true);
                  setMfaError(null);
                  try {
                    const res = await api.platformMfaRecoveryCodesGenerate(accessToken);
                    setRecoveryReveal(res.codes);
                    await loadMfa();
                  } catch (e) {
                    setMfaError(e instanceof Error ? e.message : "Generation failed");
                  } finally {
                    setMfaBusy(false);
                  }
                })();
              }}
            >
              {mfaStatus.recovery_codes_unused ? "Regenerate recovery codes" : "Generate recovery codes"}
            </button>
          </div>
        </section>
      ) : null}

      <section className="card platform-policy-card">
        <h2>Policy snapshot</h2>
        <ul className="platform-policy-list">
          <li>Platform and tenant sessions are stored separately and scoped by JWT <code>am</code>.</li>
          <li>Signing out other sessions here affects only platform console logins for your operator account.</li>
          <li>
            Platform MFA and recovery are documented in <code>docs/PLATFORM_MFA.md</code> and{" "}
            <code>docs/PLATFORM_AUTH_HARDENING.md</code>.
          </li>
        </ul>
      </section>

      <div className="row-actions">
        <button type="button" disabled={busy || !refreshToken} onClick={() => void onLogoutOthers()}>
          Sign out other platform sessions
        </button>
        <button type="button" disabled={busy} onClick={() => void loadSessions()}>
          Refresh list
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="table-wrap">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Current</th>
              <th>Scope</th>
              <th>Device / agent</th>
              <th>IP</th>
              <th>Last used</th>
              <th>Expires</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => {
              const active = !s.revoked_at && new Date(s.expires_at) > new Date();
              return (
                <tr key={s.id}>
                  <td>{s.is_current ? "Yes" : ""}</td>
                  <td>{s.auth_mode}</td>
                  <td className="cell-clip" title={s.user_agent ?? undefined}>
                    {s.device_label || s.user_agent || "Unknown"}
                  </td>
                  <td>{s.ip_address || "—"}</td>
                  <td>{formatTs(s.last_used_at)}</td>
                  <td>{formatTs(s.expires_at)}</td>
                  <td>{active ? "active" : s.revoked_at ? "revoked" : "expired"}</td>
                  <td>
                    {active && !s.is_current ? (
                      <button type="button" disabled={busy} onClick={() => void onRevoke(s.id)}>
                        Revoke
                      </button>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
