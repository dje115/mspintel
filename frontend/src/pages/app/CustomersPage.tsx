import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import type { CustomerListResponse } from "../../api/types";
import { useSession } from "../../state/session";

export function CustomersPage() {
  const { accessToken, currentTenantId } = useSession();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CustomerListResponse | null>(null);

  useEffect(() => {
    if (!accessToken || !currentTenantId) return;
    void api
      .customers(accessToken, currentTenantId, {
        page,
        page_size: 10,
        search: search || undefined,
        status: status || undefined
      })
      .then(setData);
  }, [accessToken, currentTenantId, page, search, status]);

  return (
    <div className="stack">
      <h1>Customers</h1>
      <div className="filters">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customers" />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="watch">Watch</option>
          <option value="at_risk">At risk</option>
        </select>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Owner</th>
              <th>Risk/Attention/Growth</th>
              <th>Next action</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/app/customers/${c.id}`}>{c.name}</Link>
                </td>
                <td>{c.status}</td>
                <td>{c.owner_name ?? "-"}</td>
                <td>
                  {c.risk_score ?? "-"}/{c.attention_score ?? "-"}/{c.growth_score ?? "-"}
                </td>
                <td>{c.next_best_action ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
        <span>
          Page {page} of {Math.max(1, Math.ceil((data?.total ?? 0) / 10))}
        </span>
        <button onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>
    </div>
  );
}
