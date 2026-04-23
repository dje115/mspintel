import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { SystemStatus } from "../../api/types";
import { APP_VERSION } from "../../config/version";
import { useSession } from "../../state/session";

export function PlatformSystemStatusPage() {
  const { accessToken } = useSession();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    void api.platformSystemStatus(accessToken).then(setStatus);
  }, [accessToken]);

  return (
    <div className="stack platform-page">
      <h1>System status</h1>
      <p className="version-tag">UI v{APP_VERSION} | API v{status?.version ?? "loading"}</p>
      <pre className="platform-pre">{JSON.stringify(status, null, 2)}</pre>
    </div>
  );
}
