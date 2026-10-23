import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../auth";

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggle(u) {
    setError("");
    try {
      await api.patch(`/admin/users/${u.id}/active`, null, {
        params: { is_active: !u.is_active },
      });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="glass card">
      <h2>Admin: users</h2>
      <p className="muted">Switch accounts on or off.</p>
      {error && <div className="msg error">{error}</div>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <span className={`badge ${u.role}`}>{u.role.replace("_", " ")}</span>
                </td>
                <td>
                  {u.is_active ? (
                    <span className="ok-text">Active</span>
                  ) : (
                    <span className="bad-text">Disabled</span>
                  )}
                </td>
                <td>
                  <button
                    className="btn small"
                    disabled={u.id === me.id}
                    onClick={() => toggle(u)}
                  >
                    {u.is_active ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}