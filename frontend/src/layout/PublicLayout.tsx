import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="tenant-public-root">
      <div className="tenant-public-inner">
        <Outlet />
      </div>
    </div>
  );
}
