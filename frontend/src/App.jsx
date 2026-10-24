import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import Jobs from "./pages/Jobs";
import Profile from "./pages/Profile";
import ExperienceSection from "./pages/ExperienceSection";
import PortfolioSection from "./pages/PortfolioSection";
import AdminUsers from "./pages/AdminUsers";

function Icon({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const ICONS = {
  jobs: (
    <Icon>
      <rect x="3" y="7" width="18" height="13" rx="3" />
      <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
      <path d="M3 13h18" />
    </Icon>
  ),
  profile: (
    <Icon>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </Icon>
  ),
  workspace: (
    <Icon>
      <rect x="3" y="3" width="8" height="8" rx="2" />
      <rect x="13" y="3" width="8" height="8" rx="2" />
      <rect x="3" y="13" width="8" height="8" rx="2" />
      <rect x="13" y="13" width="8" height="8" rx="2" />
    </Icon>
  ),
  users: (
    <Icon>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M16 4.6a3.5 3.5 0 0 1 0 6.8" />
      <path d="M18 14.2a6.5 6.5 0 0 1 3.5 5.8" />
    </Icon>
  ),
};

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
    ["/jobs", "Jobs", "jobs"],
    ["/profile", "Profile", "profile"],
  ],
  recruiter: [
    ["/jobs", "Jobs", "jobs"],
    ["/workspace", "Workspace", "workspace"],
  ],
  admin: [
    ["/admin", "Users", "users"],
    ["/jobs", "Jobs", "jobs"],
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
          <span className="avatar">{user.full_name.trim().charAt(0).toUpperCase()}</span>
          <button className="btn small" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <main className="content">
        <Routes>
          <Route path="/jobs" element={<Jobs />} />
          {user.role === "job_seeker" && <Route path="/profile" element={<ProfilePage />} />}
          {user.role === "recruiter" && <Route path="/workspace" element={<Workspace />} />}
          {user.role === "admin" && <Route path="/admin" element={<AdminUsers />} />}
          <Route path="*" element={<Navigate to={home} replace />} />
        </Routes>
      </main>

      <nav className="nav">
        {tabs.map(([to, label, icon]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {ICONS[icon]}
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
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