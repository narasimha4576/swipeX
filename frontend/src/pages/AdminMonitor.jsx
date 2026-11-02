import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";

function Stat({ title, value, sub }) {
  return (
    <div className="stat">
      <div className="muted small">{title}</div>
      <div className="stat-num">{value}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}

const pairs = (obj) =>
  Object.entries(obj ?? {})
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
    .join(" | ") || "none";

const total = (obj) => Object.values(obj ?? {}).reduce((a, b) => a + b, 0);

export default function AdminMonitor() {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/admin/overview")
      .then(({ data }) => setD(data))
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (error) return <div className="msg error">{error}</div>;
  if (!d) return <p className="muted">Loading...</p>;

  return (
    <>
      <section className="glass card">
        <h2>Monitor</h2>
        <p className="muted">Totals for the whole platform. No personal details. Reload the page to refresh.</p>
        <div className="stat-grid">
          <Stat title="Users" value={d.users_active + d.users_disabled} sub={pairs(d.users_by_role)} />
          <Stat title="Disabled accounts" value={d.users_disabled} />
          <Stat title="New signups" value={d.signups_7d} sub={`last 7 days (${d.signups_30d} in 30 days)`} />
          <Stat title="Jobs" value={d.jobs_total} sub={`${d.jobs_active} open | ${d.jobs_posted_on_swipex} posted on SwipeX`} />
          <Stat title="Applications" value={total(d.applications_by_status)} sub={pairs(d.applications_by_status)} />
          <Stat title="Swipes" value={total(d.swipes)} sub={`right = liked, left = skipped. ${pairs(d.swipes)}`} />
          <Stat title="Companies" value={total(d.companies_by_verification)} sub={pairs(d.companies_by_verification)} />
          <Stat title="Saved searches" value={d.saved_searches} />
          <Stat title="Public profiles" value={d.public_profiles} />
        </div>
      </section>

      <section className="glass card">
        <h3>Latest signups</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {d.recent_signups.map((u) => (
                <tr key={u.id}>
                  <td>
                    <Link className="link" to={"/admin/users/" + u.id}>
                      {u.full_name}
                    </Link>
                  </td>
                  <td>{u.role.replace("_", " ")}</td>
                  <td>{new Date(u.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="glass card">
        <h3>Admin activity log</h3>
        <p className="muted small">Every time an admin opens an account page or switches an account on or off.</p>
        {d.activity_log.length === 0 && <p className="muted">Nothing yet.</p>}
        {d.activity_log.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Admin</th>
                  <th>Action</th>
                  <th>About</th>
                </tr>
              </thead>
              <tbody>
                {d.activity_log.map((a, i) => (
                  <tr key={i}>
                    <td>{new Date(a.when).toLocaleString()}</td>
                    <td>{a.admin}</td>
                    <td>{a.action.replace(/_/g, " ")}</td>
                    <td>{a.target ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}