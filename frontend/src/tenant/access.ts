import type { MeResponse } from "../api/types";

/** Mirrors server ``ai:configure`` for tenant workspace UX (hide destructive controls). */
export function tenantHasAiConfigure(me: MeResponse | null, tenantId: string | null): boolean {
  if (!me || !tenantId) return false;
  if (me.is_platform_admin) return true;
  return me.memberships.some((m) => m.tenant_id === tenantId && m.role_code === "tenant_admin");
}
