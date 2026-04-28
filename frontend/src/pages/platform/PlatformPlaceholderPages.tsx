type PlaceholderTone = "coming-soon" | "partially-connected";

function PlatformPlaceholder({
  title,
  description,
  tone,
  nextSteps
}: {
  title: string;
  description: string;
  tone: PlaceholderTone;
  nextSteps: string;
}) {
  const badgeLabel = tone === "coming-soon" ? "Coming soon" : "Partially connected";

  return (
    <div className="stack platform-page">
      <header>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </header>
      <section className="card">
        <p>
          <span className="tenant-badge tenant-badge--muted">{badgeLabel}</span>
        </p>
        <p className="muted small-print">{nextSteps}</p>
      </section>
    </div>
  );
}

export function PlatformConnectorsPage() {
  return (
    <PlatformPlaceholder
      title="Connector estate"
      description="Platform-wide connector inventory, health and governance controls."
      tone="partially-connected"
      nextSteps="Tenant-level integrations are live. Platform-level rollup and controls are staged for a later pass."
    />
  );
}

export function PlatformAuditPage() {
  return (
    <PlatformPlaceholder
      title="Audit stream"
      description="Cross-tenant audit review for configuration and workflow changes."
      tone="coming-soon"
      nextSteps="Audit events are captured by services, but a dedicated platform UI timeline is not wired yet."
    />
  );
}

export function PlatformSettingsPage() {
  return (
    <PlatformPlaceholder
      title="Platform settings"
      description="Global operational settings and defaults for tenant environments."
      tone="coming-soon"
      nextSteps="Current configuration still uses environment and service defaults. Editable platform settings are planned."
    />
  );
}
