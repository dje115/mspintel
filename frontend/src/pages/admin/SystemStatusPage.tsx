import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { APP_VERSION } from "../../config/version";
import type { SystemStatus } from "../../api/types";
import { useSession } from "../../state/session";

export function SystemStatusPage() {
  const { accessToken, currentTenantId } = useSession();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api.systemStatus(accessToken, currentTenantId).then(setStatus);
  }, [accessToken, currentTenantId]);

  return (
    <div className="stack">
      <h1>System status</h1>
      <p className="version-tag">UI v{APP_VERSION} | API v{status?.version ?? "loading"}</p>
      <pre>{JSON.stringify(status, null, 2)}</pre>
    </div>
  );
}
