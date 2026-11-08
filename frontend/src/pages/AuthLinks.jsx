import { Link } from "react-router-dom";

export default function AuthLinks() {
  return (
    <div className="legal-footer">
      <Link to="/forgot">Forgot your password?</Link> | <Link to="/feedback?type=problem">Report a problem</Link>
    </div>
  );
}