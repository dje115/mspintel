import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../api/client";
import type { AIProviderSafe, TenantAiSettingsResponse, TenantAiTaskRouteRow } from "../../api/types";
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
  const [providers, setProviders] = useState<AIProviderSafe[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [defaultsDraft, setDefaultsDraft] = useState({
    default_ai_provider_id: "",
    default_model: "",
    fallback_ai_provider_id: "",
    fallback_model: ""
  });
  const [routeDrafts, setRouteDrafts] = useState<
    Record<string, { ai_provider_id: string; model: string; fallback_ai_provider_id: string; fallback_model: string }>
  >({});
  const [newProvider, setNewProvider] = useState({
    provider_family: "openai",
    deployment_mode: "hosted",
    display_label: "",
    base_url: "",
    api_key: "",
    model: ""
  });
  const [editProviders, setEditProviders] = useState<
    Record<string, { display_label: string; base_url: string; is_enabled: boolean; api_key: string; model: string }>
  >({});

  const providerBadgeTone = (mode: string | null): string => {
    if (!mode) return "tenant-badge tenant-badge--muted";
    if (mode.includes("local") || mode.includes("self")) return "tenant-badge tenant-badge--watch";
    if (mode.includes("microsoft")) return "tenant-badge tenant-badge--at_risk";
    return "tenant-badge tenant-badge--active";
  };

  const providerOptions = useMemo(
    () => [
      { family: "openai", mode: "hosted", label: "OpenAI (hosted)" },
      { family: "azure_openai", mode: "microsoft_hosted", label: "Azure OpenAI" },
      { family: "anthropic", mode: "hosted", label: "Anthropic" },
      { family: "google_gemini", mode: "hosted", label: "Google Gemini" },
      { family: "microsoft_copilot", mode: "microsoft_hosted", label: "Microsoft Copilot-aligned" },
      { family: "openrouter", mode: "hosted", label: "OpenRouter" },
      { family: "ollama", mode: "local", label: "Ollama (local)" },
      { family: "vllm", mode: "self_hosted", label: "vLLM (self-hosted)" },
      { family: "lm_studio", mode: "local", label: "LM Studio-compatible" },
      { family: "openai_compatible", mode: "self_hosted", label: "Custom OpenAI-compatible" }
    ],
    []
  );

  const load = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      const [s, r, providerRows] = await Promise.all([
        api.getAiSettings(accessToken, currentTenantId),
        api.getAiTaskRoutes(accessToken, currentTenantId),
        api.listAiProviders(accessToken, currentTenantId)
      ]);
      setSettings(s);
      setRoutes(r);
      setProviders(providerRows);
      setDefaultsDraft({
        default_ai_provider_id: s.default_ai_provider?.id ?? "",
        default_model: s.default_model ?? "",
        fallback_ai_provider_id: s.fallback_ai_provider?.id ?? "",
        fallback_model: s.fallback_model ?? ""
      });
      setRouteDrafts(
        Object.fromEntries(
          r.map((row) => [
            row.id,
            {
              ai_provider_id: row.ai_provider?.id ?? "",
              model: row.model ?? "",
              fallback_ai_provider_id: row.fallback_ai_provider?.id ?? "",
              fallback_model: row.fallback_model ?? ""
            }
          ])
        )
      );
      setEditProviders(
        Object.fromEntries(
          providerRows.map((p) => [
            p.id,
            {
              display_label: p.display_label ?? "",
              base_url: p.base_url ?? "",
              is_enabled: p.is_enabled,
              api_key: "",
              model: ""
            }
          ])
        )
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load AI settings");
    }
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onSaveRoute = async (row: TenantAiTaskRouteRow, enabledOverride?: boolean) => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    const draft = routeDrafts[row.id];
    setBusy(true);
    setError(null);
    try {
      await api.patchAiTaskRoutes(accessToken, currentTenantId, {
        routes: [
          {
            task_type: row.task_type,
            ai_provider_id: draft?.ai_provider_id || null,
            model: draft?.model || null,
            fallback_ai_provider_id: draft?.fallback_ai_provider_id || null,
            fallback_model: draft?.fallback_model || null,
            prompt_key: row.prompt_key,
            enabled: enabledOverride ?? row.enabled
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

  const onSaveDefaults = async () => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchAiSettings(accessToken, currentTenantId, {
        default_ai_provider_id: defaultsDraft.default_ai_provider_id || null,
        default_model: defaultsDraft.default_model || null,
        fallback_ai_provider_id: defaultsDraft.fallback_ai_provider_id || null,
        fallback_model: defaultsDraft.fallback_model || null
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save defaults");
    } finally {
      setBusy(false);
    }
  };

  const onCreateProvider = async () => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    setBusy(true);
    setError(null);
    try {
      await api.createAiProvider(accessToken, currentTenantId, {
        provider_family: newProvider.provider_family,
        deployment_mode: newProvider.deployment_mode,
        display_label: newProvider.display_label || null,
        base_url: newProvider.base_url || null,
        settings: {
          api_key: newProvider.api_key || undefined,
          model: newProvider.model || undefined
        }
      });
      setNewProvider((v) => ({ ...v, api_key: "", model: "", display_label: "" }));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider create failed");
    } finally {
      setBusy(false);
    }
  };

  const onUpdateProvider = async (providerId: string) => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    const draft = editProviders[providerId];
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchAiProvider(accessToken, currentTenantId, providerId, {
        display_label: draft.display_label || null,
        base_url: draft.base_url || null,
        is_enabled: draft.is_enabled,
        settings: {
          api_key: draft.api_key || undefined,
          model: draft.model || undefined
        }
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider update failed");
    } finally {
      setBusy(false);
    }
  };

  const onDeleteProvider = async (providerId: string) => {
    if (!accessToken || !currentTenantId || !canConfigure) return;
    if (!window.confirm("Remove this provider? Routes/defaults that reference it will be cleared.")) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteAiProvider(accessToken, currentTenantId, providerId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Provider delete failed");
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
        {canConfigure ? (
          <div className="tenant-grid tenant-grid--cards-4" style={{ marginTop: "0.9rem" }}>
            <label>
              Default provider
              <select
                className="tenant-select"
                value={defaultsDraft.default_ai_provider_id}
                onChange={(e) => setDefaultsDraft((v) => ({ ...v, default_ai_provider_id: e.target.value }))}
              >
                <option value="">None</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_label ?? p.provider_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Default model
              <input
                className="tenant-input"
                value={defaultsDraft.default_model}
                onChange={(e) => setDefaultsDraft((v) => ({ ...v, default_model: e.target.value }))}
                placeholder="gpt-4o-mini"
              />
            </label>
            <label>
              Fallback provider
              <select
                className="tenant-select"
                value={defaultsDraft.fallback_ai_provider_id}
                onChange={(e) => setDefaultsDraft((v) => ({ ...v, fallback_ai_provider_id: e.target.value }))}
              >
                <option value="">None</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_label ?? p.provider_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Fallback model
              <input
                className="tenant-input"
                value={defaultsDraft.fallback_model}
                onChange={(e) => setDefaultsDraft((v) => ({ ...v, fallback_model: e.target.value }))}
                placeholder="llama3.1"
              />
            </label>
          </div>
        ) : null}
        {canConfigure ? (
          <div style={{ marginTop: "0.75rem" }}>
            <button type="button" className="tenant-btn-primary" disabled={busy} onClick={() => void onSaveDefaults()}>
              Save defaults
            </button>
          </div>
        ) : null}
        {!canConfigure ? (
          <p className="tenant-page-sub" style={{ marginTop: "0.75rem" }}>
            Only tenant administrators (or platform operators) can change these settings.
          </p>
        ) : null}
      </section>

      <section className="tenant-card" style={{ marginBottom: "1.25rem" }}>
        <h2 className="tenant-page-title" style={{ fontSize: "1.1rem" }}>
          Providers
        </h2>
        <p className="tenant-page-sub">
          Add hosted or self-hosted providers. Secrets are encrypted at rest and never returned raw after save.
        </p>
        {canConfigure ? (
          <div className="tenant-grid tenant-grid--cards-4" style={{ marginBottom: "1rem" }}>
            <label>
              Provider
              <select
                className="tenant-select"
                value={`${newProvider.provider_family}|${newProvider.deployment_mode}`}
                onChange={(e) => {
                  const [provider_family, deployment_mode] = e.target.value.split("|");
                  setNewProvider((v) => ({ ...v, provider_family, deployment_mode }));
                }}
              >
                {providerOptions.map((o) => (
                  <option key={`${o.family}|${o.mode}`} value={`${o.family}|${o.mode}`}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Display label
              <input
                className="tenant-input"
                value={newProvider.display_label}
                onChange={(e) => setNewProvider((v) => ({ ...v, display_label: e.target.value }))}
                placeholder="Production OpenAI"
              />
            </label>
            <label>
              Base URL (optional)
              <input
                className="tenant-input"
                value={newProvider.base_url}
                onChange={(e) => setNewProvider((v) => ({ ...v, base_url: e.target.value }))}
                placeholder="https://api.openai.com/v1"
              />
            </label>
            <label>
              Default model (optional)
              <input
                className="tenant-input"
                value={newProvider.model}
                onChange={(e) => setNewProvider((v) => ({ ...v, model: e.target.value }))}
                placeholder="gpt-4o-mini"
              />
            </label>
            <label>
              API key / token
              <input
                className="tenant-input"
                type="password"
                value={newProvider.api_key}
                onChange={(e) => setNewProvider((v) => ({ ...v, api_key: e.target.value }))}
                placeholder="sk-..."
              />
            </label>
          </div>
        ) : null}
        {canConfigure ? (
          <button type="button" className="tenant-btn-primary" disabled={busy} onClick={() => void onCreateProvider()}>
            Add provider
          </button>
        ) : null}
        <div className="tenant-table-wrap" style={{ marginTop: "0.9rem" }}>
          <table className="tenant-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Family</th>
                <th>Type</th>
                <th>Configured</th>
                <th>Enabled</th>
                {canConfigure ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div>{p.display_label ?? p.provider_name}</div>
                    <div className="muted" style={{ fontSize: "0.78rem" }}>{p.base_url ?? "Default endpoint"}</div>
                  </td>
                  <td>{familyLabel(p.provider_family)}</td>
                  <td>
                    <span className={providerBadgeTone(p.deployment_mode)}>{p.deployment_mode?.replace(/_/g, " ") ?? "—"}</span>
                  </td>
                  <td>{p.has_encrypted_settings ? "Yes" : "No"}</td>
                  <td>{p.is_enabled ? "Yes" : "No"}</td>
                  {canConfigure ? (
                    <td>
                      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                        <button
                          type="button"
                          className="tenant-btn-ghost"
                          disabled={busy}
                          onClick={() =>
                            setEditProviders((m) => ({
                              ...m,
                              [p.id]: { ...(m[p.id] ?? { display_label: "", base_url: "", is_enabled: true, api_key: "", model: "" }), is_enabled: !p.is_enabled }
                            }))
                          }
                        >
                          Toggle
                        </button>
                        <button type="button" className="tenant-btn-ghost" disabled={busy} onClick={() => void onUpdateProvider(p.id)}>
                          Save
                        </button>
                        <button type="button" className="tenant-btn-ghost" disabled={busy} onClick={() => void onDeleteProvider(p.id)}>
                          Remove
                        </button>
                      </div>
                      <div className="tenant-grid tenant-grid--cards-3" style={{ marginTop: "0.45rem" }}>
                        <input
                          className="tenant-input"
                          value={editProviders[p.id]?.display_label ?? ""}
                          placeholder="Display label"
                          onChange={(e) =>
                            setEditProviders((m) => ({ ...m, [p.id]: { ...(m[p.id] ?? { display_label: "", base_url: "", is_enabled: p.is_enabled, api_key: "", model: "" }), display_label: e.target.value } }))
                          }
                        />
                        <input
                          className="tenant-input"
                          value={editProviders[p.id]?.base_url ?? ""}
                          placeholder="Base URL"
                          onChange={(e) =>
                            setEditProviders((m) => ({ ...m, [p.id]: { ...(m[p.id] ?? { display_label: "", base_url: "", is_enabled: p.is_enabled, api_key: "", model: "" }), base_url: e.target.value } }))
                          }
                        />
                        <input
                          className="tenant-input"
                          type="password"
                          value={editProviders[p.id]?.api_key ?? ""}
                          placeholder="New API key/token (optional)"
                          onChange={(e) =>
                            setEditProviders((m) => ({ ...m, [p.id]: { ...(m[p.id] ?? { display_label: "", base_url: "", is_enabled: p.is_enabled, api_key: "", model: "" }), api_key: e.target.value } }))
                          }
                        />
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
                  <td>
                    {canConfigure ? (
                      <input
                        className="tenant-input"
                        style={{ minWidth: "10rem" }}
                        value={routeDrafts[r.id]?.model ?? ""}
                        onChange={(e) =>
                          setRouteDrafts((m) => ({ ...m, [r.id]: { ...(m[r.id] ?? { ai_provider_id: "", model: "", fallback_ai_provider_id: "", fallback_model: "" }), model: e.target.value } }))
                        }
                        placeholder="model"
                      />
                    ) : (
                      r.model ?? "—"
                    )}
                  </td>
                  <td>
                    <code style={{ fontSize: "0.85em" }}>{r.prompt_key}</code>
                  </td>
                  {canConfigure ? (
                    <td>
                      <select
                        className="tenant-select"
                        value={routeDrafts[r.id]?.ai_provider_id ?? ""}
                        onChange={(e) =>
                          setRouteDrafts((m) => ({
                            ...m,
                            [r.id]: { ...(m[r.id] ?? { ai_provider_id: "", model: "", fallback_ai_provider_id: "", fallback_model: "" }), ai_provider_id: e.target.value }
                          }))
                        }
                        style={{ marginBottom: "0.35rem" }}
                      >
                        <option value="">Use defaults</option>
                        {providers.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.display_label ?? p.provider_name}
                          </option>
                        ))}
                      </select>
                      <div style={{ display: "flex", gap: "0.35rem" }}>
                        <button
                          type="button"
                          className="tenant-btn-ghost"
                          disabled={busy}
                          onClick={() => void onSaveRoute(r)}
                        >
                          Save
                        </button>
                      <button
                        type="button"
                        className="tenant-btn-ghost"
                        disabled={busy}
                        onClick={() => void onSaveRoute(r, !r.enabled)}
                      >
                        {r.enabled ? "Disable" : "Enable"}
                      </button>
                      </div>
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
