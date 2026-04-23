import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { TenantAiSettingsResponse, TenantAiTaskRouteRow } from "../../api/types";
import { tenantHasAiConfigure } from "../../tenant/access";
import { useSession } from "../../state/session";

function WarningBanner() {
  return (
    <div
      className="tenant-card"
      style={{
        marginBottom: "1.25rem",
        borderLeft: "4px solid #c27803",
        background: "rgba(194, 120, 3, 0.08)"
      }}
    >
      <strong>Before you change AI routing</strong>
      <p className="tenant-page-sub" style={{ marginTop: "0.35rem", marginBottom: 0 }}>
        Switching models or providers can affect cost, latency, privacy posture, and output quality. Disabling a task
        stops that workflow from running. Test changes in a safe tenant where possible, and use prompt versioning to
        roll back if behaviour regresses.
      </p>
    </div>
  );
}

function familyLabel(family: string | null) {
  if (!family) return "—";
  return family.replace(/_/g, " ");
}

export function AiSettingsPage() {
  const { accessToken, currentTenantId, me } = useSession();
  const canConfigure = tenantHasAiConfigure(me, currentTenantId);
  const [settings, setSettings] = useState<TenantAiSettingsResponse | null>(null);
  const [routes, setRoutes] = useState<TenantAiTaskRouteRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      const [s, r] = await Promise.all([
        api.getAiSettings(accessToken, currentTenantId),
        api.getAiTaskRoutes(accessToken, currentTenantId)
      ]);
      setSettings(s);
      setRoutes(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load AI settings");
    }
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onToggleRoute = async (row: TenantAiTaskRouteRow) => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchAiTaskRoutes(accessToken, currentTenantId, {
        routes: [
          {
            task_type: row.task_type,
            ai_provider_id: row.ai_provider?.id ?? null,
            model: row.model,
            fallback_ai_provider_id: row.fallback_ai_provider?.id ?? null,
            fallback_model: row.fallback_model,
            prompt_key: row.prompt_key,
            enabled: !row.enabled
          }
        ]
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">AI engines &amp; routing</h1>
        <p className="tenant-page-sub">
          Tenant-scoped defaults and per-task routing. Hosted API providers and self-hosted endpoints (for example
          Ollama or OpenAI-compatible gateways) are modelled with <strong>provider family</strong> and{" "}
          <strong>deployment mode</strong> so operators can see how inference runs.
        </p>
      </header>

      <WarningBanner />

      {error ? (
        <p className="tenant-page-sub" style={{ color: "#b42318" }}>
          {error}
        </p>
      ) : null}

      <section className="tenant-card" style={{ marginBottom: "1.25rem" }}>
        <h2 className="tenant-page-title" style={{ fontSize: "1.1rem" }}>
          Workspace defaults
        </h2>
        {!settings ? (
          <p className="tenant-page-sub">Loading…</p>
        ) : (
          <dl style={{ display: "grid", gridTemplateColumns: "160px 1fr", rowGap: "0.5rem", columnGap: "1rem" }}>
            <dt className="tenant-page-sub">Default provider</dt>
            <dd>
              {settings.default_ai_provider ? (
                <>
                  <span className="tenant-badge tenant-badge--muted">{familyLabel(settings.default_ai_provider.provider_family)}</span>{" "}
                  <span className="tenant-badge tenant-badge--muted">
                    {settings.default_ai_provider.deployment_mode?.replace(/_/g, " ") ?? "—"}
                  </span>
                  <div style={{ marginTop: "0.25rem" }}>{settings.default_ai_provider.display_label ?? settings.default_ai_provider.provider_name}</div>
                </>
              ) : (
                "—"
              )}
            </dd>
            <dt className="tenant-page-sub">Default model</dt>
            <dd>{settings.default_model ?? "—"}</dd>
            <dt className="tenant-page-sub">Fallback</dt>
            <dd>
              {settings.fallback_ai_provider ? (
                <span className="tenant-badge tenant-badge--muted">{familyLabel(settings.fallback_ai_provider.provider_family)}</span>
              ) : (
                "—"
              )}{" "}
              {settings.fallback_model ? `· ${settings.fallback_model}` : null}
            </dd>
          </dl>
        )}
        {!canConfigure ? (
          <p className="tenant-page-sub" style={{ marginTop: "0.75rem" }}>
            Only tenant administrators (or platform operators) can change these settings.
          </p>
        ) : null}
      </section>

      <section className="tenant-card">
        <h2 className="tenant-page-title" style={{ fontSize: "1.1rem" }}>
          Task routing
        </h2>
        <p className="tenant-page-sub">Each row maps an AI task type to a prompt key and optional provider override.</p>
        <div className="tenant-table-wrap">
          <table className="tenant-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Enabled</th>
                <th>Provider</th>
                <th>Deployment</th>
                <th>Model</th>
                <th>Prompt key</th>
                {canConfigure ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {routes.map((r) => (
                <tr key={r.id}>
                  <td>{r.task_type.replace(/_/g, " ")}</td>
                  <td>{r.enabled ? <span className="tenant-badge tenant-badge--active">On</span> : <span className="tenant-badge tenant-badge--muted">Off</span>}</td>
                  <td>{familyLabel(r.ai_provider?.provider_family ?? null)}</td>
                  <td>{r.ai_provider?.deployment_mode?.replace(/_/g, " ") ?? "—"}</td>
                  <td>{r.model ?? "—"}</td>
                  <td>
                    <code style={{ fontSize: "0.85em" }}>{r.prompt_key}</code>
                  </td>
                  {canConfigure ? (
                    <td>
                      <button
                        type="button"
                        className="tenant-btn-ghost"
                        disabled={busy}
                        onClick={() => void onToggleRoute(r)}
                      >
                        {r.enabled ? "Disable" : "Enable"}
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
