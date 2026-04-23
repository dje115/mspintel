import { useAppShellState } from "./app/state/appShellState";

function App() {
  const shell = useAppShellState();

  return (
    <main className="app-shell">
      <section className="app-card">
        <h1>mspintel platform is running</h1>
        <p>React + TypeScript frontend is online and ready for SaaS feature development.</p>

        <ul className="route-outline">
          <li>Public pages scaffold: {shell.publicArea}</li>
          <li>Authenticated app scaffold: {shell.appArea}</li>
          <li>Platform admin scaffold: {shell.platformAdminArea}</li>
          <li>Tenant admin scaffold: {shell.tenantAdminArea}</li>
          <li>Onboarding scaffold: {shell.onboardingArea}</li>
          <li>Tenant switcher scaffold: {shell.tenantSwitcherArea}</li>
        </ul>
      </section>
    </main>
  );
}

export default App;
