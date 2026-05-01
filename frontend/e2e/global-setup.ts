/**
 * Prepares Playwright storageState (tenant JWT in localStorage) and e2e/.cache/meta.json.
 * Backend URL: E2E_API_BASE_URL, else inside Docker `/.dockerenv` → http://backend:8000, else host http://127.0.0.1:8001.
 */
import fs from "fs";
import path from "path";

import type { FullConfig } from "@playwright/test";

function resolveApiBase(): string {
  let raw: string;
  if (process.env.E2E_API_BASE_URL?.trim()) {
    raw = process.env.E2E_API_BASE_URL.trim();
  } else {
    try {
      raw = fs.existsSync("/.dockerenv") ? "http://backend:8000" : "http://127.0.0.1:8001";
    } catch {
      raw = "http://127.0.0.1:8001";
    }
  }
  return raw.replace(/\/$/, "");
}

async function globalSetup(config: FullConfig) {
  const apiBase = resolveApiBase();
  const email = process.env.E2E_TENANT_EMAIL || "tenant-admin@demo-msp.example.com";
  const password = process.env.E2E_TENANT_PASSWORD || "ChangeMe123!";

  const loginRes = await fetch(`${apiBase}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!loginRes.ok) {
    const t = await loginRes.text();
    throw new Error(`E2E global-setup: login failed HTTP ${loginRes.status}: ${t.slice(0, 400)}`);
  }
  const pair = (await loginRes.json()) as {
    access_token: string;
    refresh_token: string;
    session_id: string;
  };

  const meRes = await fetch(`${apiBase}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${pair.access_token}` }
  });
  if (!meRes.ok) {
    throw new Error(`E2E global-setup: /auth/me failed HTTP ${meRes.status}`);
  }
  const me = (await meRes.json()) as { memberships?: { tenant_id: string }[] };
  const tenantId = me.memberships?.[0]?.tenant_id;
  if (!tenantId) {
    throw new Error("E2E global-setup: no tenant membership on demo user");
  }

  const tenantHeaders = {
    Authorization: `Bearer ${pair.access_token}`,
    "X-Tenant-Id": tenantId
  };

  let customerId: string | null = null;
  const readFirstCustomer = async (): Promise<string | null> => {
    const custRes = await fetch(`${apiBase}/api/v1/customers?page=1&page_size=10`, { headers: tenantHeaders });
    if (!custRes.ok) return null;
    const custJson = (await custRes.json()) as { items?: { id: string }[] };
    return custJson.items?.[0]?.id ?? null;
  };

  customerId = await readFirstCustomer();

  if (!customerId && process.env.E2E_SKIP_CONNECTOR_PREP !== "1") {
    const connRes = await fetch(`${apiBase}/api/v1/integrations/connections`, { headers: tenantHeaders });
    if (connRes.ok) {
      const connections = (await connRes.json()) as { id: string; system_type: string }[];
      const m365 = connections.find((c) => c.system_type === "microsoft_365");
      if (m365) {
        const syncRes = await fetch(`${apiBase}/api/v1/integrations/connections/${m365.id}/sync`, {
          method: "POST",
          headers: { ...tenantHeaders, "Content-Type": "application/json" }
        });
        if (!syncRes.ok && syncRes.status !== 202) {
          const t = await syncRes.text();
          console.warn(`E2E global-setup: M365 sync HTTP ${syncRes.status}: ${t.slice(0, 300)}`);
        }
        customerId = await readFirstCustomer();
      }
    }
  }

  const baseURL = (config.projects[0]?.use?.baseURL as string) || process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";
  const origin = new URL(baseURL).origin;

  const authDir = path.join(process.cwd(), "e2e", ".auth");
  const cacheDir = path.join(process.cwd(), "e2e", ".cache");
  fs.mkdirSync(authDir, { recursive: true });
  fs.mkdirSync(cacheDir, { recursive: true });

  const storageState = {
    cookies: [] as { name: string; value: string; domain: string; path: string }[],
    origins: [
      {
        origin,
        localStorage: [
          { name: "mspintel_access_token", value: pair.access_token },
          { name: "mspintel_refresh_token", value: pair.refresh_token },
          { name: "mspintel_session_id", value: String(pair.session_id) },
          { name: "mspintel_tenant_id", value: tenantId }
        ]
      }
    ]
  };
  fs.writeFileSync(path.join(authDir, "tenant.json"), JSON.stringify(storageState, null, 2));
  fs.writeFileSync(
    path.join(cacheDir, "meta.json"),
    JSON.stringify({ tenantId, customerId, apiBase }, null, 2)
  );
}

export default globalSetup;
