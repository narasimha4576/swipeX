import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import AuthPage from "./pages/AuthPage";
import Profile from "./pages/Profile";
import ExperienceSection from "./pages/ExperienceSection";
import PortfolioSection from "./pages/PortfolioSection";
import AdminUsers from "./pages/AdminUsers";

function Shell() {
  const { user, loading, logout } = useAuth();

  if (loading) return <div className="center muted">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;

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

      <main className="content">
        {user.role === "job_seeker" && (
          <>
            <Profile />
            <ExperienceSection />
            <PortfolioSection />
          </>
        )}
        {user.role === "admin" && <AdminUsers />}
        {user.role === "recruiter" && (
          <section className="glass card">
            <h2>Recruiter workspace</h2>
            <p className="muted">
              Posting jobs and reviewing applicants arrive in the coming days.
            </p>
          </section>
        )}
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