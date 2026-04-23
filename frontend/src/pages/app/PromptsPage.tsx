import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../api/client";
import type { PromptDetailResponse, PromptListItem } from "../../api/types";
import { useSession } from "../../state/session";
import { tenantHasAiConfigure } from "../../tenant/access";

function PromptWarning() {
  return (
    <div
      className="tenant-card"
      style={{
        marginBottom: "1.25rem",
        borderLeft: "4px solid #b42318",
        background: "rgba(180, 35, 24, 0.06)"
      }}
    >
      <strong>Prompts change live behaviour</strong>
      <p className="tenant-page-sub" style={{ marginTop: "0.35rem", marginBottom: 0 }}>
        Edits can materially change recommendations, triage, drafting, and summaries. Prefer creating a new version,
        validating in a non-production tenant, then activating. You can roll back by activating an older version or
        reverting to the platform default when no tenant override is required.
      </p>
    </div>
  );
}

export function PromptsPage() {
  const { accessToken, currentTenantId, me } = useSession();
  const canConfigure = tenantHasAiConfigure(me, currentTenantId);
  const [items, setItems] = useState<PromptListItem[]>([]);
  const [detail, setDetail] = useState<PromptDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newNote, setNewNote] = useState("");
  const [newText, setNewText] = useState("");
  const [ovKey, setOvKey] = useState("");
  const [ovTitle, setOvTitle] = useState("");
  const [ovText, setOvText] = useState("");

  const loadList = useCallback(async () => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      const rows = await api.listPrompts(accessToken, currentTenantId);
      setItems(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prompts");
    }
  }, [accessToken, currentTenantId]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const platformKeys = useMemo(() => items.filter((i) => i.source === "platform").map((i) => i.prompt_key), [items]);

  const openDetail = async (definitionId: string) => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    try {
      const d = await api.getPromptDetail(accessToken, currentTenantId, definitionId);
      setDetail(d);
      setNewText("");
      setNewNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load prompt");
    }
  };

  const onAddVersion = async () => {
    if (!accessToken || !currentTenantId || !detail || !newText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.addPromptVersion(accessToken, currentTenantId, detail.definition_id, {
        prompt_text: newText,
        change_note: newNote || null
      });
      setDetail(d);
      setNewText("");
      setNewNote("");
      await loadList();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add version");
    } finally {
      setBusy(false);
    }
  };

  const onActivate = async (versionId: string) => {
    if (!accessToken || !currentTenantId || !detail) return;
    if (!window.confirm("Activate this version for this tenant? This affects live AI behaviour.")) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.activatePromptVersion(accessToken, currentTenantId, detail.definition_id, versionId);
      setDetail(d);
      await loadList();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Activation failed");
    } finally {
      setBusy(false);
    }
  };

  const onRevert = async (promptKey: string) => {
    if (!accessToken || !currentTenantId) return;
    if (!window.confirm("Remove the tenant override and revert to the platform default for this prompt key?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.revertPromptToDefault(accessToken, currentTenantId, promptKey);
      setDetail(null);
      await loadList();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Revert failed");
    } finally {
      setBusy(false);
    }
  };

  const onCreateOverride = async () => {
    if (!accessToken || !currentTenantId || !ovKey || !ovTitle.trim() || !ovText.trim()) return;
    const row = items.find((i) => i.prompt_key === ovKey);
    if (!row) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.createTenantPromptOverride(accessToken, currentTenantId, {
        prompt_key: ovKey,
        title: ovTitle,
        task_type: row?.task_type ?? "recommendation_generation",
        initial_version: { prompt_text: ovText, change_note: "Tenant override" }
      });
      setDetail(d);
      setOvKey("");
      setOvTitle("");
      setOvText("");
      await loadList();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create override");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Prompts</h1>
        <p className="tenant-page-sub">
          Versioned prompts with platform defaults and optional tenant overrides. Stable keys (for example{" "}
          <code>ticket_triage.system</code>) tie runtime tasks to the correct definition.
        </p>
      </header>

      <PromptWarning />

      {error ? (
        <p className="tenant-page-sub" style={{ color: "#b42318" }}>
          {error}
        </p>
      ) : null}

      <div className="tenant-table-wrap">
        <table className="tenant-table">
          <thead>
            <tr>
              <th>Prompt key</th>
              <th>Task</th>
              <th>Source</th>
              <th>Active version</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.definition_id}>
                <td>
                  <code style={{ fontSize: "0.85em" }}>{row.prompt_key}</code>
                </td>
                <td>{row.task_type.replace(/_/g, " ")}</td>
                <td>
                  {row.source === "tenant_override" ? (
                    <span className="tenant-badge tenant-badge--watch">Tenant override</span>
                  ) : (
                    <span className="tenant-badge tenant-badge--muted">Platform default</span>
                  )}
                </td>
                <td>{row.active_version_number ?? "—"}</td>
                <td>
                  <button type="button" className="tenant-btn-ghost" onClick={() => void openDetail(row.definition_id)}>
                    View / history
                  </button>
                  {canConfigure && row.source === "tenant_override" ? (
                    <button
                      type="button"
                      className="tenant-btn-ghost"
                      style={{ marginLeft: "0.5rem" }}
                      disabled={busy}
                      onClick={() => void onRevert(row.prompt_key)}
                    >
                      Revert to platform default
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canConfigure && platformKeys.length > 0 ? (
        <section className="tenant-card" style={{ marginTop: "1.5rem" }}>
          <h2 className="tenant-page-title" style={{ fontSize: "1.05rem" }}>
            Create tenant override
          </h2>
          <p className="tenant-page-sub">Pick a platform prompt key, then publish an initial version for this tenant.</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
            <label className="tenant-page-sub">
              Prompt key
              <select className="tenant-select" value={ovKey} onChange={(e) => setOvKey(e.target.value)} style={{ display: "block", marginTop: "0.25rem", minWidth: "220px" }}>
                <option value="">Select…</option>
                {platformKeys.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </label>
            <label className="tenant-page-sub">
              Title
              <input className="tenant-select" value={ovTitle} onChange={(e) => setOvTitle(e.target.value)} style={{ display: "block", marginTop: "0.25rem", minWidth: "200px" }} />
            </label>
            <button type="button" className="tenant-btn-primary" disabled={busy || !ovKey} onClick={() => void onCreateOverride()}>
              Create override
            </button>
          </div>
          <label className="tenant-page-sub" style={{ display: "block", marginTop: "0.75rem" }}>
            Initial prompt text
            <textarea
              className="tenant-select"
              value={ovText}
              onChange={(e) => setOvText(e.target.value)}
              rows={5}
              style={{ display: "block", marginTop: "0.35rem", width: "100%", maxWidth: "640px" }}
            />
          </label>
        </section>
      ) : null}

      {detail ? (
        <section className="tenant-card" style={{ marginTop: "1.5rem" }}>
          <h2 className="tenant-page-title" style={{ fontSize: "1.05rem" }}>
            {detail.title}{" "}
            <span className="tenant-badge tenant-badge--muted">{detail.scope}</span>
          </h2>
          <p className="tenant-page-sub">{detail.description ?? "—"}</p>
          <h3 className="tenant-page-sub" style={{ fontWeight: 600, marginTop: "1rem" }}>
            Versions
          </h3>
          <div className="tenant-table-wrap">
            <table className="tenant-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Active</th>
                  <th>Note</th>
                  <th>Created</th>
                  {canConfigure && detail.scope === "tenant" ? <th /> : null}
                </tr>
              </thead>
              <tbody>
                {detail.versions.map((v) => (
                  <tr key={v.id}>
                    <td>{v.version_number}</td>
                    <td>{v.is_active ? <span className="tenant-badge tenant-badge--active">Active</span> : "—"}</td>
                    <td>{v.change_note ?? "—"}</td>
                    <td>{new Date(v.created_at).toLocaleString()}</td>
                    {canConfigure && detail.scope === "tenant" ? (
                      <td>
                        {!v.is_active ? (
                          <button type="button" className="tenant-btn-ghost" disabled={busy} onClick={() => void onActivate(v.id)}>
                            Activate
                          </button>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {canConfigure && detail.scope === "tenant" ? (
            <div style={{ marginTop: "1rem" }}>
              <h3 className="tenant-page-sub" style={{ fontWeight: 600 }}>
                New version (draft)
              </h3>
              <p className="tenant-page-sub">Creates a new inactive version; activate it after review.</p>
              <textarea
                className="tenant-select"
                placeholder="Prompt body"
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                rows={6}
                style={{ width: "100%", maxWidth: "720px", display: "block", marginBottom: "0.5rem" }}
              />
              <input
                className="tenant-select"
                placeholder="Change note"
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                style={{ maxWidth: "420px", marginRight: "0.5rem" }}
              />
              <button type="button" className="tenant-btn-primary" disabled={busy || !newText.trim()} onClick={() => void onAddVersion()}>
                Save version
              </button>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
