import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import Jobs from "./pages/Jobs";
import Profile from "./pages/Profile";
import ExperienceSection from "./pages/ExperienceSection";
import PortfolioSection from "./pages/PortfolioSection";
import AdminUsers from "./pages/AdminUsers";

function ProfilePage() {
  return (
    <>
      <Profile />
      <ExperienceSection />
      <PortfolioSection />
    </>
  );
}

function Workspace() {
  return (
    <section className="glass card">
      <h2>Recruiter workspace</h2>
      <p className="muted">
        Posting jobs and reviewing applicants arrive in the coming days.
      </p>
    </section>
  );
}

const TABS = {
  job_seeker: [
    ["/jobs", "Jobs"],
    ["/profile", "Profile"],
  ],
  recruiter: [
    ["/jobs", "Jobs"],
    ["/workspace", "Workspace"],
  ],
  admin: [
    ["/admin", "Users"],
    ["/jobs", "Jobs"],
  ],
};

function Shell() {
  const { user, loading, logout } = useAuth();

  if (loading) return <div className="center muted">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;

  const tabs = TABS[user.role];
  const home = tabs[0][0];

  return (
    <div className="app">
      <header className="topbar glass">
        <div className="brand">
          Swipe<span className="accent">X</span>
        </div>
        <div className="who">
          <span className="name">{user.full_name}</span>
          <span className={`badge ${user.role}`}>{user.role.replace("_", " ")}</span>
          <button className="btn small" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <nav className="nav">
        {tabs.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <main className="content">
        <Routes>
          <Route path="/jobs" element={<Jobs />} />
          {user.role === "job_seeker" && <Route path="/profile" element={<ProfilePage />} />}
          {user.role === "recruiter" && <Route path="/workspace" element={<Workspace />} />}
          {user.role === "admin" && <Route path="/admin" element={<AdminUsers />} />}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/*" element={<Shell />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}