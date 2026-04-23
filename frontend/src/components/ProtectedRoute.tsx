import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../state/session";

export function ProtectedRoute() {
  const { accessToken, loading } = useSession();
  const location = useLocation();

  if (loading) return <div className="page-wrap">Loading...</div>;
  if (!accessToken) return <Navigate to="/login" replace state={{ from: location }} />;

  return <Outlet />;
}
