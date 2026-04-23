import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <main className="public-wrap">
      <section className="public-card">
        <Outlet />
      </section>
    </main>
  );
}
