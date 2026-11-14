import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../authContext";
import ThemeToggle from "./ThemeToggle";
import LegalFooter from "./LegalFooter";

const STEPS = [
  ["Make your profile", "Add a headline, your skills and a PDF resume. SwipeX reads the resume to find your skills."],
  ["Swipe or search", "Swipe cards right to save and left to skip, or search with filters for country, remote, level and skills."],
  ["Check before you apply", "See your skills match, a safety check on the posting, and evidence that the company is real."],
  ["Apply and track", "Apply on SwipeX, or fill the company form with the Chrome extension. Track every job from Saved to Interview."],
];

const FEATURES = [
  ["Real jobs", "Openings are imported from the official job boards of real companies, plus clearly labelled third-party sources."],
  ["Resume match", "A skills match percentage on every job, a resume health score, and AI tips that may only reword facts already in your resume."],
  ["Safety check", "Flags fees, ID or OTP requests, WhatsApp-only contact, personal emails and unrealistic pay before you share anything."],
  ["Company trust card", "Official board, website over HTTPS, domain age, public records and how often the company answers applicants."],
  ["One-click autofill", "A Chrome extension fills Greenhouse, Lever and Ashby forms. It never submits for you and never answers diversity questions."],
  ["Private by design", "Admins see account basics and counts only. Download all your data or delete your account at any time."],
];

const FAQ = [
  ["Is it free?", "Yes. SwipeX is a free beta run as a portfolio project. It uses free servers, so the first page after a quiet period can take about 30 seconds."],
  ["Will it email me?", "No. Notifications appear in the app, and a forgotten password is reset with recovery codes you save once. Keep them somewhere safe."],
  ["Does autofill submit my application?", "No. It fills the form and marks what it filled. You check everything and press Submit yourself."],
  ["Who can see my resume?", "Only the recruiters of a company you apply to on SwipeX. Admins cannot open resumes, and a public profile never shows your email, phone or resume."],
  ["I am a recruiter. What can I do?", "Set up a company, post jobs, invite colleagues with a code, and review applicants. Postings that ask candidates for money are blocked."],
];

export default function Landing() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Loading...</div>;
  if (user) return <Navigate to="/home" replace />;

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="brand">
          Swipe<span className="accent">X</span>
        </div>
        <nav className="lp-links">
          <a className="lp-plain" href="#how">How it works</a>
          <a className="lp-plain" href="#features">Features</a>
          <a className="lp-plain" href="#faq">FAQ</a>
          <ThemeToggle />
          <Link className="btn small" to="/login">Log in</Link>
        </nav>
      </header>

      <section className="lp-hero">
        <div>
          <h1>Find jobs worth applying to.</h1>
          <p className="lp-lead">
            Swipe through real openings, see how well your resume matches, check that the company is genuine, and fill
            application forms in one click.
          </p>
          <div className="actions">
            <Link className="btn primary lp-cta-btn" to="/login?mode=register">Create a free account</Link>
            <Link className="btn lp-cta-btn" to="/login">Log in</Link>
          </div>
          <p className="muted small" style={{ marginTop: "0.9rem" }}>
            Free beta. It runs on a free server, so the first load can take about 30 seconds.
          </p>
        </div>

        <div className="lp-card" aria-hidden="true">
          <div className="lp-card-tag">Example card</div>
          <div className="job-top">
            <div className="logo">A</div>
            <div className="job-title">
              <h3>Backend Engineer</h3>
              <div className="muted small">Acme Labs</div>
            </div>
          </div>
          <div className="meta">
            <span>Remote</span>
            <span>Full-time</span>
            <span>Fresher</span>
          </div>
          <div className="chips">
            <span className="chip">Python</span>
            <span className="chip">FastAPI</span>
            <span className="chip">SQL</span>
          </div>
          <div className="match-pill strong" style={{ marginTop: "0.8rem" }}>86% skills match</div>
          <div className="lp-card-actions">
            <span className="btn small">Skip</span>
            <span className="btn small primary-inline">Save</span>
          </div>
        </div>
      </section>

      <section className="lp-strip">
        <span>Official company job boards</span>
        <span>Match on every job</span>
        <span>No email needed</span>
        <span>Delete your data any time</span>
      </section>

      <section id="how" className="lp-section">
        <h2>How it works</h2>
        <div className="lp-grid">
          {STEPS.map(([title, text], i) => (
            <div className="lp-box" key={title}>
              <div className="lp-num">{i + 1}</div>
              <h3>{title}</h3>
              <p className="muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="features" className="lp-section">
        <h2>What you get</h2>
        <div className="lp-grid">
          {FEATURES.map(([title, text]) => (
            <div className="lp-box" key={title}>
              <h3>{title}</h3>
              <p className="muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="faq" className="lp-section">
        <h2>Questions</h2>
        <div className="lp-faq">
          {FAQ.map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p className="muted">{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="lp-final">
        <h2>Ready to try it?</h2>
        <p className="muted">It takes a minute to sign up. Save your recovery codes, then start swiping.</p>
        <Link className="btn primary lp-cta-btn" to="/login?mode=register">Create a free account</Link>
      </section>

      <LegalFooter />
    </div>
  );
}