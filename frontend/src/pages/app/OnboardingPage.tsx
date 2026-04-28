import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { TenantMspProfile, TenantServiceCatalogEntry } from "../../api/types";
import { useSession } from "../../state/session";

const DEFAULT_SERVICES: TenantServiceCatalogEntry[] = [
  { service_key: "managed_support", service_name: "Managed support", is_selected: false, is_custom: false, sort_order: 0 },
  { service_key: "m365_management", service_name: "Microsoft 365 management", is_selected: false, is_custom: false, sort_order: 1 },
  { service_key: "backup_disaster_recovery", service_name: "Backup / disaster recovery", is_selected: false, is_custom: false, sort_order: 2 },
  { service_key: "security", service_name: "Security", is_selected: false, is_custom: false, sort_order: 3 },
  { service_key: "network", service_name: "Network", is_selected: false, is_custom: false, sort_order: 4 },
  { service_key: "cloud", service_name: "Cloud", is_selected: false, is_custom: false, sort_order: 5 },
  { service_key: "identity_mfa_conditional_access", service_name: "Identity / MFA / conditional access", is_selected: false, is_custom: false, sort_order: 6 },
  { service_key: "endpoint_management", service_name: "Endpoint management", is_selected: false, is_custom: false, sort_order: 7 },
  { service_key: "compliance", service_name: "Compliance", is_selected: false, is_custom: false, sort_order: 8 },
  { service_key: "projects_migrations", service_name: "Projects / migrations", is_selected: false, is_custom: false, sort_order: 9 },
  { service_key: "vcio_qbr", service_name: "vCIO / QBR", is_selected: false, is_custom: false, sort_order: 10 },
  { service_key: "telephony", service_name: "Telephony", is_selected: false, is_custom: false, sort_order: 11 },
  { service_key: "procurement_licensing_resale", service_name: "Procurement / licensing resale", is_selected: false, is_custom: false, sort_order: 12 }
];

const EMPTY_PROFILE: Omit<TenantMspProfile, "tenant_id"> = {
  legal_name: null,
  brand_name: null,
  regions_served: [],
  vertical_focus: [],
  team_size_band: null,
  customer_count_band: null,
  typical_customer_size_band: null,
  delivery_model: null,
  business_goals: [],
  free_text_description: null
};

export function OnboardingPage() {
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<{ status: string; step: string } | null>(null);
  const [profile, setProfile] = useState<Omit<TenantMspProfile, "tenant_id">>(EMPTY_PROFILE);
  const [catalog, setCatalog] = useState<TenantServiceCatalogEntry[]>(DEFAULT_SERVICES);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [customService, setCustomService] = useState("");

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setError(null);
    Promise.all([
      api.currentTenantOnboarding(accessToken, currentTenantId),
      api.tenantProfile(accessToken, currentTenantId),
      api.tenantServiceCatalogue(accessToken, currentTenantId)
    ])
      .then(([onboarding, p, c]) => {
        setData(onboarding);
        setProfile({
          legal_name: p.legal_name,
          brand_name: p.brand_name,
          regions_served: p.regions_served || [],
          vertical_focus: p.vertical_focus || [],
          team_size_band: p.team_size_band,
          customer_count_band: p.customer_count_band,
          typical_customer_size_band: p.typical_customer_size_band,
          delivery_model: p.delivery_model,
          business_goals: p.business_goals || [],
          free_text_description: p.free_text_description
        });
        setCatalog((c.items || []).length > 0 ? c.items : DEFAULT_SERVICES);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load onboarding profile"));
  }, [accessToken, currentTenantId]);

  const setArrayValue = (key: "regions_served" | "vertical_focus" | "business_goals", value: string) => {
    setProfile((prev) => ({
      ...prev,
      [key]: value
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean)
    }));
  };

  const saveAll = async () => {
    if (!accessToken || !currentTenantId) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateTenantProfile(accessToken, currentTenantId, profile);
      await api.updateTenantServiceCatalogue(accessToken, currentTenantId, {
        tenant_id: currentTenantId,
        items: catalog.map((s, idx) => ({ ...s, sort_order: idx }))
      });
      const next = await api.updateOnboarding(accessToken, currentTenantId, { status: "in_progress", step: "profile_catalogue" });
      setData(next);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save onboarding profile");
    } finally {
      setSaving(false);
    }
  };

  const addCustomService = () => {
    const name = customService.trim();
    if (!name) return;
    const key = `custom_${name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`;
    setCatalog((prev) => [...prev, { service_key: key, service_name: name, is_selected: true, is_custom: true, sort_order: prev.length }]);
    setCustomService("");
  };

  return (
    <div>
      <header className="tenant-page-head">
        <h1 className="tenant-page-title">Workspace onboarding</h1>
        <p className="tenant-page-sub">
          Complete these steps so your MSP gets the most from customer intelligence, integrations, and team access.
        </p>
      </header>
      {error ? <p className="tenant-error">{error}</p> : null}

      <section className="tenant-panel">
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Progress</h2>
          <Link className="tenant-panel-link" to="/app">
            Go to dashboard
          </Link>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1.25rem 1.35rem" }}>
          {!data ? (
            <div className="tenant-skeleton">Loading onboarding state…</div>
          ) : (
            <ul className="tenant-list-plain" style={{ paddingLeft: "1.25rem" }}>
              <li>
                <strong>Status:</strong> {data.status}
              </li>
              <li>
                <strong>Current step:</strong> {data.step}
              </li>
              <li>Connect PSA / RMM under Integrations when connectors are enabled.</li>
              <li>Invite your delivery and sales leads from Team &amp; invites.</li>
            </ul>
          )}
        </div>
      </section>

      <section className="tenant-panel" style={{ marginTop: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">MSP business profile</h2>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.2rem", display: "grid", gap: "0.65rem" }}>
          <input className="tenant-input" placeholder="Legal name" value={profile.legal_name ?? ""} onChange={(e) => setProfile((p) => ({ ...p, legal_name: e.target.value || null }))} />
          <input className="tenant-input" placeholder="Brand name" value={profile.brand_name ?? ""} onChange={(e) => setProfile((p) => ({ ...p, brand_name: e.target.value || null }))} />
          <input className="tenant-input" placeholder="Regions served (comma separated)" value={profile.regions_served.join(", ")} onChange={(e) => setArrayValue("regions_served", e.target.value)} />
          <input className="tenant-input" placeholder="Vertical focus (comma separated)" value={profile.vertical_focus.join(", ")} onChange={(e) => setArrayValue("vertical_focus", e.target.value)} />
          <input className="tenant-input" placeholder="Business goals (comma separated)" value={profile.business_goals.join(", ")} onChange={(e) => setArrayValue("business_goals", e.target.value)} />
          <input className="tenant-input" placeholder="Team size band" value={profile.team_size_band ?? ""} onChange={(e) => setProfile((p) => ({ ...p, team_size_band: e.target.value || null }))} />
          <input className="tenant-input" placeholder="Customer count band" value={profile.customer_count_band ?? ""} onChange={(e) => setProfile((p) => ({ ...p, customer_count_band: e.target.value || null }))} />
          <input className="tenant-input" placeholder="Typical customer size band" value={profile.typical_customer_size_band ?? ""} onChange={(e) => setProfile((p) => ({ ...p, typical_customer_size_band: e.target.value || null }))} />
          <input className="tenant-input" placeholder="Delivery model" value={profile.delivery_model ?? ""} onChange={(e) => setProfile((p) => ({ ...p, delivery_model: e.target.value || null }))} />
          <textarea className="tenant-review-notes" rows={5} placeholder="Describe what your MSP does, focus areas, strengths, and ideal customers." value={profile.free_text_description ?? ""} onChange={(e) => setProfile((p) => ({ ...p, free_text_description: e.target.value || null }))} />
        </div>
      </section>

      <section className="tenant-panel" style={{ marginTop: "1rem" }}>
        <div className="tenant-panel-head">
          <h2 className="tenant-panel-title">Service catalogue</h2>
        </div>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.2rem" }}>
          <div className="tenant-list-plain">
            {catalog.map((item, idx) => (
              <label key={`${item.service_key}-${idx}`} className="tenant-rec-card" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={item.is_selected}
                  onChange={(e) =>
                    setCatalog((prev) => prev.map((x, i) => (i === idx ? { ...x, is_selected: e.target.checked } : x)))
                  }
                />
                <span>{item.service_name}</span>
              </label>
            ))}
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
            <input className="tenant-input" placeholder="Add custom service" value={customService} onChange={(e) => setCustomService(e.target.value)} />
            <button className="tenant-btn-inline tenant-btn-inline--ghost" type="button" onClick={addCustomService}>
              Add
            </button>
          </div>
        </div>
      </section>

      <section className="tenant-panel" style={{ marginTop: "1rem" }}>
        <div className="tenant-panel-body" style={{ padding: "1rem 1.2rem" }}>
          <button type="button" className="tenant-btn-inline" disabled={saving} onClick={saveAll}>
            {saving ? "Saving..." : "Save onboarding profile"}
          </button>
        </div>
      </section>
    </div>
  );
}
