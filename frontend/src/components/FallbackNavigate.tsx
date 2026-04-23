import { Navigate, useLocation } from "react-router-dom";

export function FallbackNavigate() {
  const { pathname } = useLocation();
  if (pathname.startsWith("/platform")) {
    return <Navigate to="/platform/login" replace />;
  }
  return <Navigate to="/login" replace />;
}
