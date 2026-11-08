import { NavLink, useLocation } from "react-router-dom";

export default function FeedbackLink() {
  const { pathname } = useLocation();
  return (
    <NavLink
      className="bell-btn"
      to={`/feedback?from=${encodeURIComponent(pathname)}`}
      title="Send feedback or report a problem"
      aria-label="Send feedback or report a problem"
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </NavLink>
  );
}