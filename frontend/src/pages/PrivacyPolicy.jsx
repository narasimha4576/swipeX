import { Link } from "react-router-dom";
import { LEGAL } from "../legalInfo";

export default function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <div className="brand">
        Swipe<span className="accent">X</span>
      </div>
      <h1>Privacy Policy</h1>
      <p className="muted">Last updated {LEGAL.updated}</p>

      <h2>1. Who we are</h2>
      <p>
        {LEGAL.product} is a job-discovery website run by {LEGAL.operator} in {LEGAL.country}. You can contact us at{" "}
        {LEGAL.contactEmail}.
      </p>

      <h2>2. What we collect</h2>
      <p>What you give us:</p>
      <ul>
        <li>Your account: name, email and password. The password is stored only as a one-way scramble (a hash), never as text.</li>
        <li>
          Your profile, if you are a job seeker: headline, location, bio, skills, years of experience, work
          experience, education, portfolio links and a photo.
        </li>
        <li>
          Application details you save so forms can be filled for you: phone number, profile links, college and
          degree, work authorisation, notice period, salary figures and a cover letter.
        </li>
        <li>Resumes: the PDF files you upload and the text we read from them to find skills.</li>
        <li>
          What you do: jobs you like or skip, jobs you apply to and their status, your saved searches and your
          notifications.
        </li>
        <li>Recovery codes for resetting your password. They are stored only as one-way scrambles, and each works once.</li>
        <li>
          Feedback and problem reports you send: your message, the page you were on and a short description of your
          browser. Your name and email are included only if you tick the box that allows contact, or type an email.
        </li>
        <li>If you are a recruiter: company details, job postings and your place in a company team.</li>
      </ul>
      <p>
        Your browser stores a sign-in token and your light or dark choice in its local storage. We do not currently use
        advertising or analytics trackers.
      </p>

      <h2>3. Who can see your information</h2>
      <ul>
        <li>
          <b>You</b> can see and change everything above.
        </li>
        <li>
          <b>Recruiters</b> see your details only when you apply to a job from their company: your name, email,
          headline, location, skills, bio, experience, portfolio, the resume you chose and your application status.
          Everyone on that company's team can see this.
        </li>
        <li>
          <b>Anyone with your link</b>, but only if you switch on your public profile: your name, photo, headline,
          location, bio, skills, experience, education and portfolio links. It never shows your email, phone number,
          salary details or resumes. We ask search engines not to list it, but anyone who has the link can open it.
        </li>
        <li>
          <b>SwipeX administrators</b> see only account basics (name, email, role, whether the account is active, and
          the join date) and simple counts such as how many resumes and applications you have. They do not see your
          profile contents, resumes or application details. Every time an administrator opens an account, it is written
          to a log.
        </li>
        <li>
          <b>SwipeX administrators</b> also read the feedback and problem reports people send. They see your name and
          email on a report only if you allowed contact.
        </li>
        <li>Job postings and company details are public by nature.</li>
      </ul>
      <p>We do not sell your information and we do not show advertising.</p>

      <h2>4. Other services that receive information</h2>
      <ul>
        <li>
          <b>An AI service (Groq)</b> receives text only when you use an AI feature. For company summaries it receives
          public company information. For AI answers to application questions it receives the question and a few facts
          such as skills, degree and years of experience. For resume tips it receives your resume text with email
          addresses, phone numbers and links removed. It does not receive your password or your email. AI answers can
          be wrong, so check them before you use them.
        </li>
        <li>
          If switched on, company searches send only the company name to Wikidata, a web search service and YouTube.
        </li>
        <li>Job listings come from public job-board services. We do not send your information to them.</li>
      </ul>

      <h2>5. How long we keep it</h2>
      <ul>
        <li>We keep your information while your account exists.</li>
        <li>Jobs you skip are removed automatically after 15 days.</li>
        <li>
          When you delete your account we erase your profile, resumes, photo, applications, liked and skipped jobs,
          saved searches and notifications.
        </li>
        <li>
          Job postings and the company record stay (closed) so other people keep their application history. They are
          no longer linked to you.
        </li>
        <li>
          Feedback and problem reports are kept until the administrator deletes them. If you delete your account, your
          reports stay but are no longer linked to you.
        </li>
        <li>If we keep backups, deleted data may remain in them for a limited time.</li>
      </ul>

      <h2>6. Your choices</h2>
      <p>
        On the <Link to="/account">Account page</Link> you can download a copy of your data and delete your account. In
        your profile you can edit or remove anything, delete resumes, and turn your public profile off.
      </p>

      <h2>7. Security</h2>
      <p>
        We protect your information with hashed passwords, limits on sign-in attempts, checks on uploaded files and
        strict rules about who can open what. No website is perfectly secure, so please use a strong password that you
        do not use anywhere else.
      </p>

      <h2>8. Children</h2>
      <p>SwipeX is for people aged 18 and over.</p>

      <h2>9. Changes</h2>
      <p>If we change this policy we will update the date at the top. For big changes we will tell you in the app.</p>

      <h2>10. Contact</h2>
      <p>
        Questions or requests about your information: {LEGAL.contactEmail}. See also our <Link to="/terms">Terms</Link>.
      </p>
    </div>
  );
}