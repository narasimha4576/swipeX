import { Link } from "react-router-dom";

export default function LegalFooter() {
  return (
    <footer className="legal-footer">
      By using SwipeX you agree to the <Link to="/terms">Terms</Link> and the{" "}
      <Link to="/privacy">Privacy Policy</Link>.
    </footer>
  );
}