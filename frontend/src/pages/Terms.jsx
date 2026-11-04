import { Link } from "react-router-dom";
import { LEGAL } from "../legalInfo";

export default function Terms() {
  return (
    <div className="legal-page">
      <div className="brand">
        Swipe<span className="accent">X</span>
      </div>
      <h1>Terms of Use</h1>
      <p className="muted">Last updated {LEGAL.updated}</p>

      <h2>1. Using SwipeX</h2>
      <p>
        SwipeX helps people find jobs and helps companies find people. By creating an account or using the site you agree
        to these terms and to our <Link to="/privacy">Privacy Policy</Link>. You must be 18 or older.
      </p>

      <h2>2. Your account</h2>
      <ul>
        <li>Give true information and keep your password private. One account is for one person.</li>
        <li>You are responsible for what happens under your account.</li>
        <li>You can delete your account at any time from the Account page.</li>
      </ul>

      <h2>3. Job seekers</h2>
      <ul>
        <li>Do not claim skills, jobs or qualifications you do not have.</li>
        <li>
          Some job listings are collected from other websites. They are marked as third-party and have not been checked
          by SwipeX. Always check a company yourself before you share personal details, and never pay money to get a job.
        </li>
        <li>
          AI features, such as match scores, summaries and resume tips, can be wrong. You are responsible for anything
          you send to an employer.
        </li>
      </ul>

      <h2>4. Recruiters and companies</h2>
      <ul>
        <li>Post only real jobs that you are allowed to offer.</li>
        <li>
          Never ask applicants for money, fees, bank details or identity documents. SwipeX blocks postings that look like
          this and may close the company's postings and accounts.
        </li>
        <li>Use applicants' details only to consider them for the job they applied to, and keep them private.</li>
        <li>You are responsible for the people you invite to your company's team.</li>
      </ul>

      <h2>5. What you must not do</h2>
      <ul>
        <li>Break the law, harass anyone, or post false or misleading content.</li>
        <li>Upload files with viruses or hidden scripts, or try to break into or overload SwipeX.</li>
        <li>Copy large amounts of data from SwipeX with automated tools without our permission.</li>
        <li>Pretend to be someone else or open accounts in bulk.</li>
      </ul>

      <h2>6. Your content</h2>
      <p>
        You keep ownership of what you upload, such as your profile and resumes. You allow SwipeX to store it and show it
        to the people described in the Privacy Policy so the service can work.
      </p>

      <h2>7. No promises about jobs</h2>
      <p>
        SwipeX does not guarantee that you will find a job or a candidate, that listings are accurate, or that the site
        will always be available. The service is provided as it is.
      </p>

      <h2>8. Ending access</h2>
      <p>
        We may close postings or accounts that break these terms. You may stop using SwipeX and delete your account at any
        time.
      </p>

      <h2>9. Limits on our responsibility</h2>
      <p>
        To the extent the law allows, {LEGAL.operator} is not responsible for losses that come from using SwipeX, from
        third-party listings, or from AI answers.
      </p>

      <h2>10. Changes and law</h2>
      <p>
        We may update these terms and will change the date above when we do. These terms follow the laws of{" "}
        {LEGAL.country}.
      </p>

      <h2>11. Contact</h2>
      <p>{LEGAL.contactEmail}</p>
    </div>
  );
}