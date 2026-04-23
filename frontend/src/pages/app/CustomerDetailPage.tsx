import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerDetailResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function CustomerDetailPage() {
  const { id } = useParams();
  const { accessToken, currentTenantId } = useSession();
  const [data, setData] = useState<CustomerDetailResponse | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId || !id) return;
    void api.customerDetail(accessToken, currentTenantId, id).then(setData);
  }, [accessToken, currentTenantId, id]);

  if (!data) return <div>Loading customer...</div>;

  return (
    <div className="stack">
      <h1>{data.name}</h1>
      <p>Status: {data.status} | Owner: {data.owner_name ?? "-"}</p>

      <div className="cards">
        <article className="card">Risk: {data.latest_scores?.risk_score ?? "-"}</article>
        <article className="card">Attention: {data.latest_scores?.attention_score ?? "-"}</article>
        <article className="card">Growth: {data.latest_scores?.growth_score ?? "-"}</article>
      </div>

      <div className="cards">
        <article className="card">Open tickets: {data.open_tickets_count}</article>
        <article className="card">Open opportunities: {data.open_opportunities_count}</article>
        <article className="card">Open/lost quotes: {data.open_quotes_count}</article>
      </div>

      <section>
        <h2>Recommendations</h2>
        <ul>{data.recommendation_summary.map((r) => <li key={r}>{r}</li>)}</ul>
      </section>

      <section>
        <h2>Recent actions</h2>
        <ul>{data.recent_actions.map((a) => <li key={a}>{a}</li>)}</ul>
      </section>

      <section>
        <h2>Placeholder sections</h2>
        <p>Overview | Support trends | Opportunities & quotes | Actions/log</p>
      </section>
    </div>
  );
}
