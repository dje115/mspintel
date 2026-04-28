import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { TenantAIContext } from "../api/types";
import { useSession } from "../state/session";

export function TenantAiContextNotice(props: { compact?: boolean }) {
  const { compact = false } = props;
  const { accessToken, currentTenantId } = useSession();
  const [ctx, setCtx] = useState<TenantAIContext | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    setLoading(true);
    setErr(null);
    void api
      .tenantAiContext(accessToken, currentTenantId)
      .then(setCtx)
      .catch((e: unknown) => {
        setCtx(null);
        setErr(e instanceof Error ? e.message : "Unable to load tenant AI context");
      })
      .finally(() => setLoading(false));
  }, [accessToken, currentTenantId]);

  const health = useMemo(() => {
    if (!ctx) return { label: "Low confidence", tone: "tenant-badge tenant-badge--watch" };
    const hasProfile = !!(ctx.msp_profile_summary.brand_name || ctx.msp_profile_summary.legal_name);
    const hasServices = ctx.selected_services.length > 0;
    if (!hasProfile && !hasServices) return { label: "Needs onboarding", tone: "tenant-badge tenant-badge--at_risk" };
    if (!hasProfile || !hasServices) return { label: "Low confidence", tone: "tenant-badge tenant-badge--watch" };
    return { label: "Live data", tone: "tenant-badge tenant-badge--active" };
  }, [ctx]);

  return (
    <section className="tenant-card" style={{ marginBottom: compact ? "0.75rem" : "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", flexWrap: "wrap" }}>
        <p className="tenant-page-sub" style={{ margin: 0 }}>
          AI output quality depends on tenant MSP profile + selected service catalogue context.
        </p>
        <span className={health.tone}>{health.label}</span>
      </div>
      {loading ? <p className="muted" style={{ margin: "0.45rem 0 0" }}>Checking context…</p> : null}
      {err ? <p className="tenant-error" style={{ marginTop: "0.55rem" }}>{err}</p> : null}
      {!loading && !err && ctx ? (
        <p className="muted" style={{ margin: "0.55rem 0 0", fontSize: "0.82rem" }}>
          Services: {ctx.selected_services.length} · Goals: {ctx.business_goals.length} · Regions: {ctx.regions_served.length}.
          {ctx.data_confidence_notes.length > 0 ? ` ${ctx.data_confidence_notes[0]}` : ""}
          {" "}
          <Link to="/app/onboarding">Update onboarding</Link>
          {" · "}
          <Link to="/app/integrations">connectors</Link>
          {" · "}
          <Link to="/app/integrations/mappings">mapping review</Link>
        </p>
      ) : null}
    </section>
  );
}
