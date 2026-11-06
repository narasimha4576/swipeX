import { fromServer } from "../time";
import { useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../authContext";

function label(key) {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function show(key, value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (key.endsWith("_at")) return fromServer(value).toLocaleString();
  return String(value);
}

function Facts({ data }) {
  if (!data) return <p className="muted">Nothing here.</p>;
  return (
    <dl className="facts">
      {Object.entries(data).map(([key, value]) => (
        <div className="fact" key={key}>
          <dt>{label(key)}</dt>
          <dd>{show(key, value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function AdminUserDetail() {
  const { id } = useParams();
  const { user: me } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api
      .get(`/admin/users/${id}/detail`)
      .then(({ data }) => setData(data))
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

  async function toggleActive() {
    setError("");
    try {
      await api.patch(`/admin/users/${id}/active`, null, {
        params: { is_active: !data.account.is_active },
      });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (error && !data) return <div className="msg error">{error}</div>;
  if (!data) return <p className="muted">Loading...</p>;

  const account = data.account;

  return (
    <>
      <section className="glass card">
        <p>
          <Link className="link" to="/admin/users">
            Back to users
          </Link>
        </p>
        <h2 style={{ margin: 0 }}>{account.full_name}</h2>
        <div className="muted">{account.email}</div>
        <div style={{ marginTop: "0.4rem" }}>
          <span className={`badge ${account.role}`}>{account.role.replace("_", " ")}</span>{" "}
          {account.is_active ? <span className="ok-text">Active</span> : <span className="bad-text">Disabled</span>}
        </div>
        <p className="muted small" style={{ marginTop: "0.8rem" }}>
          To protect people's privacy, admins only see account basics and simple counts. Profiles, resumes and
          application details are not shown. Opening this page is recorded in the admin activity log.
        </p>
        <div className="actions">
          <button className="btn small" disabled={account.id === me.id} onClick={toggleActive}>
            {account.is_active ? "Disable account" : "Enable account"}
          </button>
        </div>
        {error && <div className="msg error">{error}</div>}
      </section>

      <section className="glass card">
        <h3>Account</h3>
        <Facts data={account} />
      </section>

      {data.company && (
        <section className="glass card">
          <h3>Company</h3>
          <Facts data={data.company} />
        </section>
      )}

      {data.summary && (
        <section className="glass card">
          <h3>Summary</h3>
          <Facts data={data.summary} />
        </section>
      )}
    </>
  );
}