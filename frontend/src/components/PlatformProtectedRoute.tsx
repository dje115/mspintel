import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../state/session";

/** Platform console: requires platform-admin user and platform-scoped JWT (`am=platform`). */
export function PlatformProtectedRoute() {
  const { accessToken, loading, me, authMode } = useSession();
  const location = useLocation();

  if (loading) return <div className="page-wrap">Loading...</div>;
  if (!accessToken) {
    return <Navigate to="/platform/login" replace state={{ from: location }} />;
  }

  if (!me) {
    return <div className="page-wrap">Loading...</div>;
  }

  if (!me.is_platform_admin || authMode !== "platform") {
    if (authMode === "tenant") {
      return <Navigate to="/app/customers" replace />;
    }
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
