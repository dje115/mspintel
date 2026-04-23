import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../state/session";

/** Tenant app shell: requires a tenant-scoped session (not platform-console JWT). */
export function TenantProtectedRoute() {
  const { accessToken, loading, me, authMode } = useSession();
  const location = useLocation();

  if (loading) return <div className="page-wrap">Loading...</div>;
  if (!accessToken) return <Navigate to="/login" replace state={{ from: location }} />;

  if (!me) return <div className="page-wrap">Loading...</div>;

  if (authMode === "platform") {
    return <Navigate to="/platform" replace />;
  }

  if (authMode === "tenant" && me.memberships.length === 0) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
