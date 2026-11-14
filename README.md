<h1 align="center">SwipeX</h1>

<p align="center">
  <b>Swipe through jobs like cards, check which companies are real, match your resume, and apply with one-click autofill.</b><br/>
  Live site: <a href="https://swipex.jobslist.workers.dev">swipex.jobslist.workers.dev</a>
</p>

<p align="center">
  <img src="https://github.com/narasimha4576/swipeX/actions/workflows/tests.yml/badge.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Status-Live%20(beta%20prep)-orange" alt="Status" />
</p>

SwipeX is a full-stack job discovery platform. Job seekers swipe right to save a job and left to skip it. Recruiters post jobs, review applicants and work in company teams. Admins keep the platform healthy without being able to read anyone's private data.

> **Status:** live on a free hosting stack. Days 1 to 46 are built, and the remaining days are beta, legal checks and launch. See the [Roadmap](#roadmap-whats-left).
> The free server sleeps after 15 idle minutes, so the first visit can take about 30 seconds.

---

## Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [How the main flows work](#how-the-main-flows-work)
4. [Data model](#data-model)
5. [Tech stack](#tech-stack)
6. [Build log](#build-log)
7. [Project structure](#project-structure)
8. [Run it locally](#run-it-locally)
9. [Run it with Docker](#run-it-with-docker-production-style)
10. [Configuration](#configuration)
11. [API overview](#api-overview)
12. [Security and privacy design](#security-and-privacy-design)
13. [Testing and CI](#testing-and-ci)
14. [Hosting plan](#hosting-plan-free-tier)
15. [Roadmap](#roadmap-whats-left)
16. [Known limits](#known-limits)

---

## What it does

| Role | What they can do |
|---|---|
| **Job seeker** | Swipe through jobs, search worldwide with filters (country, remote, level, skills, salary, freshness), see a skills match score on every card, upload up to 5 PDF resumes, get a resume health score and AI tips for one specific job, apply with a review page, track applications (Saved, Applied, Shortlisted, Interview, Rejected), save searches and get notified of new matches, autofill job forms with the Chrome extension, add a profile photo and education, share an optional public profile, download or delete all their data |
| **Recruiter** | Create a company, request verification, post and edit jobs (scam wording is blocked), review applicants with filters, shortlist, interview or reject, invite colleagues with a company invite code |
| **Admin** | Open any account page (basics and counts only), enable or disable accounts, verify companies, watch platform analytics, system health and errors, and read feedback and problem reports. Every admin action is logged |
| **Everyone** | Sign in with JWT, change password, make recovery codes, send feedback or report a problem, see notifications in the bell, switch light and dark theme, ask the help chatbot |

### Highlights

- **Live jobs** imported automatically from the official boards of real companies (Greenhouse, Lever, Ashby) plus RemoteOK, Arbeitnow and optionally Adzuna. Third-party listings are clearly labelled.
- **Safety check** on every job: flags fees, ID or OTP requests, WhatsApp-only contact, personal emails, shortened links and more. Scam-like postings from recruiters are blocked.
- **Company trust card**: official board, HTTPS website, domain age, public records and hiring response stats.
- **Company search** for any company: jobs, news, photos, videos and an optional AI summary.
- **Facts-only AI**: resume tips can only reword what is already in your resume. Invented skills or numbers are rejected by code.
- **Autofill extension** that fills Greenhouse, Lever and Ashby forms but never submits and never answers diversity questions.
- **Private by design**: admins never see profile contents, resumes or application details.
- **No email service**: notifications live in the app, and password recovery uses one-time codes.

---

## Architecture

```mermaid
flowchart LR
  subgraph Client
    B["Browser: React app"]
    X["Chrome extension: form autofill"]
  end

  subgraph Live["Live hosting"]
    CF["Cloudflare: website"]
    API["Render: FastAPI in Docker"]
    DB[("Neon: PostgreSQL")]
  end

  GA["GitHub Actions: importer every 3 hours, CI"]
  G["Groq AI: OpenAI-compatible"]
  J["Job boards: Greenhouse, Lever, Ashby, RemoteOK, Arbeitnow, Adzuna"]
  O["Company lookups: Wikidata, web search, YouTube, news"]

  B -->|"HTTPS"| CF
  B -->|"HTTPS, JWT"| API
  X -->|"scoped 30-minute token"| API
  API --> DB
  GA --> DB
  GA -->|"fetch jobs"| J
  API -->|"summaries, tips, answers"| G
  API -->|"company names only"| O
```

With Docker, **nginx** serves the website and forwards `/api` to the API, so both share one address. On the live site, the website runs on **Cloudflare** and calls the API on **Render** directly. The website is built with `VITE_API_URL`, and the API allows it through `CORS_ORIGINS`.

### From a push to the live site

```mermaid
flowchart LR
  P["git push to main"] --> CI["GitHub Actions: backend tests, undefined names, lint, build"]
  P --> CF["Cloudflare builds and publishes the website"]
  P --> RN["Render rebuilds the API when backend files change"]
  RN --> MG["Container runs alembic upgrade head, then starts the API"]
  MG --> NE[("Neon")]
```

---

## How the main flows work

### Sign in and use the API

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as API
  participant D as Database

  U->>A: POST /auth/login with email and password
  A->>D: find user and check the Argon2 hash
  A-->>U: JWT token valid for 60 minutes
  U->>A: GET /jobs with the token
  A->>D: search and filter jobs
  A-->>U: jobs with skills match scores
```

### From a posted job to a response

```mermaid
sequenceDiagram
  actor R as Recruiter
  actor A as Admin
  actor S as Job seeker
  participant App as SwipeX

  R->>App: Create company and request verification
  A->>App: Verify the company
  R->>App: Post a job
  App-->>S: Job appears in Jobs and Discover
  S->>App: Swipe right, then apply with a resume
  App-->>R: Applicant with profile and resume
  R->>App: Shortlist, interview or reject
  App-->>S: Bell notification and new status
```

### Swipe, apply and get a response

```mermaid
stateDiagram-v2
  [*] --> saved: swipe right
  saved --> applied: apply with a resume
  applied --> shortlisted: recruiter shortlists
  applied --> interview: recruiter invites
  applied --> rejected: recruiter rejects
  shortlisted --> interview
  shortlisted --> rejected
  interview --> rejected
  shortlisted --> applied: recruiter resets
  interview --> applied: recruiter resets
  rejected --> applied: recruiter resets
```

Every change after "applied" creates an in-app notification for the applicant. Jobs from official boards are applied for on the company site, and the seeker confirms with "Yes, I applied".

### Resume matching

```mermaid
flowchart LR
  R["Resume PDF"] --> P["pypdf reads the text"]
  P --> S["Skill finder"]
  P --> T["TF-IDF similarity"]
  J["Job skills and description"] --> S
  J --> T
  S --> M["Skills match percent"]
  T --> M
  M --> C["Match on cards, Jobs for you ranking, resume tips"]
  C --> F["AI tips pass a facts-only filter"]
```

### Safety check and trust card

```mermaid
flowchart TD
  J["Job or company"] --> S["Safety check on the posting text: fees, ID or OTP, WhatsApp only, personal email, shortened links, unrealistic pay"]
  J --> T["Trust card: official board, website over HTTPS, domain age, public record, hiring response rate"]
  S --> L["Risk: low, medium or high"]
  T --> E["Evidence: strong, good or limited"]
  L --> U["Shown on the job page"]
  E --> U
```

### Autofill extension

```mermaid
flowchart TD
  A["Job page: Review and autofill"] --> B["Website sends your saved details to the extension"]
  B --> C["Extension opens the company form in a new tab"]
  C --> D["Rules fill name, email, links, education and resume"]
  D --> E{"Extra questions?"}
  E -- "AI switched on" --> F["30-minute scoped token asks the API for answers"]
  E -- "AI off" --> G["Left empty"]
  F --> H["Purple outline: check these answers"]
  D --> I["Red dashed outline: still needs you"]
  H --> J["You review everything and press Submit yourself"]
  G --> J
  I --> J
  J --> K["Back in SwipeX: Yes, I applied"]
```

Questions about gender, race, disability, veteran status, pay, visa and ID are never answered by AI.

### Live job import

```mermaid
flowchart TD
  T["GitHub Actions: every 3 hours"] --> L{"Another import running?"}
  L -- yes --> SK["Skip this run"]
  L -- no --> F["Fetch jobs from all boards"]
  F --> N["Clean up: country, skills, level, salary"]
  N --> U["Add new jobs, update seen jobs, close jobs that disappeared"]
  U --> C["Delete jobs closed for 60+ days unless someone liked or applied"]
  C --> M["Check saved searches and notify users"]
  M --> R["Record the run and a heartbeat for the admin System page"]
```

A database lock makes sure two imports never run at the same time. With Docker, a separate worker runs the same import every 15 minutes.

### Forgot password (no email needed)

```mermaid
flowchart TD
  A["Account page: make 8 recovery codes"] --> B["Codes are shown once: copy or download"]
  C["Sign-in page: Forgot your password?"] --> D["Enter email, one recovery code, new password"]
  D --> E{"Code valid and unused?"}
  E -- yes --> F["Password changed, code used up, notice in the bell"]
  E -- no --> G["Same generic error, attempts are limited"]
```

Codes are stored only as keyed one-way hashes. An admin cannot reset someone else's password.

### Feedback and problem reports

```mermaid
flowchart LR
  P["Person: speech-bubble button, or login page link"] --> F["Feedback or Report a problem form"]
  F --> Q{"Allow contact?"}
  Q -- yes --> A1["Admin sees name and email"]
  Q -- no --> A2["Admin sees it as anonymous"]
  A1 --> N["Admin bell notification"]
  A2 --> N
  N --> T["Admin Feedback tab: status, private note, delete"]
```

### Admin privacy

```mermaid
flowchart LR
  AD["Admin opens an account page"] --> V["Sees name, email, role, status, join date and counts only"]
  AD --> X["Never sees profile text, resumes or application details"]
  AD --> LG["Every look and every enable or disable is written to the activity log"]
```

### Protection on every request

```mermaid
flowchart TD
  R["Incoming request"] --> H["Size limit 12 MB, security headers"]
  H --> C["CORS: only allowed websites"]
  C --> RL["Rate limits by real visitor address: login, sign-up, reset, feedback"]
  RL --> J["JWT check: signature, expiry, no scoped tokens"]
  J --> RO["Role check: seeker, recruiter or admin"]
  RO --> OW["Ownership check: your data only"]
  OW --> DB[("Database")]
  H -. "crash" .-> E["Error tracking with a reference code"]
```

---

## Data model

```mermaid
erDiagram
  USERS ||--o| PROFILES : has
  USERS ||--o{ EXPERIENCES : has
  USERS ||--o{ EDUCATIONS : has
  USERS ||--o{ PORTFOLIO_ITEMS : has
  USERS ||--o{ RESUMES : uploads
  USERS ||--o{ SWIPES : makes
  USERS ||--o{ APPLICATIONS : sends
  USERS ||--o{ SAVED_SEARCHES : saves
  USERS ||--o{ NOTIFICATIONS : receives
  USERS ||--o{ RECOVERY_CODES : owns
  USERS ||--o{ FEEDBACK : writes
  USERS ||--o| RECRUITER_PROFILES : "recruiter of"
  COMPANIES ||--o{ RECRUITER_PROFILES : "team members"
  COMPANIES ||--o| COMPANY_INVITES : "invite code"
  COMPANIES ||--o{ JOBS : posts
  JOBS ||--o{ SWIPES : "swiped on"
  JOBS ||--o{ APPLICATIONS : "applied to"
  RESUMES ||--o{ APPLICATIONS : "used in"
  APPLICATIONS ||--o{ APPLICATION_EVENTS : "status history"
  USERS ||--o{ ADMIN_AUDIT : "admin actions"
```

Other tables: `error_events` (crash reports) and `system_status` (worker heartbeat, last import).
Resumes and profile photos are stored **inside PostgreSQL** (`file_data`, `photo_data`), so the app needs no disk and works on free hosting.
One swipe and one application are allowed per user and job.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, APScheduler |
| Database | PostgreSQL 16 locally, Neon (PostgreSQL 18) when live |
| Auth | JWT (PyJWT), Argon2 password hashing (pwdlib), recovery codes |
| Frontend | React with Vite, React Router, Axios, Framer Motion, plain CSS (soft capsule theme, Nunito font) |
| AI | Groq through one OpenAI-compatible helper (summaries, resume tips, form answers, chatbot) |
| Resume tools | pypdf, scikit-learn (TF-IDF match), Pillow (photos) |
| Jobs | Greenhouse, Lever, Ashby, RemoteOK, Arbeitnow, Adzuna |
| Extension | Chrome Manifest V3 |
| Quality | pytest (254 tests), ESLint, pyflakes, GitHub Actions CI |
| Packaging and hosting | Docker, Docker Compose, nginx locally. Cloudflare, Render, Neon and GitHub Actions when live |

---

## Build log

SwipeX was built one day at a time.

| Days | What was built |
|---|---|
| 1 to 3 | Repo, FastAPI, React, PostgreSQL in Docker, the first tables |
| 4 to 6 | Sign-up, login with JWT, roles, admin user management |
| 7 to 8 | Job seeker profile, experience and portfolio |
| 9 to 10 | Sample jobs, job list, search, filters, competition level |
| 11 | Swipe cards, save, skip and undo |
| 12 to 14 | Recruiter company and job posting, resumes and applying, applicant review |
| 15 | Alembic migrations, company verification, verified-only jobs |
| 16 | Live job import from official Greenhouse boards |
| 17 | Company Trust Card (Wikidata, HTTPS, domain age, hiring stats) |
| 18 | Full job page, light and dark theme |
| 19 | Application details and review-before-apply |
| 20 | Autofill Chrome extension |
| 21 | Lever, Ashby and Adzuna sources, internships, safety check, scam blocking |
| 22 to 23 | Company search with news and AI summary, help chatbot, AI autofill answers |
| 24 | Home page, split-view Jobs, worldwide jobs, third-party sources |
| 25 to 26 | Resume reading and health check, match %, ranked "Jobs for you", AI resume tips |
| 27 to 28 | Smarter recommendations, saved searches, bell notifications |
| 30 | Company teams, job editing, applicant filters |
| 31 | Photo, education, public profile, privacy-first admin view |
| 32 to 33 | Automated tests for every area |
| 34 | Rate limits, PDF checks, security headers, CORS |
| 35 to 36 | Download and delete my data, Privacy Policy and Terms, recovery codes, feedback |
| 37 | Error tracking, health checks, worker heartbeat, System page |
| 38 | Admin analytics (counts only) |
| 39 | Docker production setup |
| 40 | Free hosting chosen: Neon, Render, Cloudflare, GitHub Actions |
| 41 | Files stored in the database, old-job cleanup, migration 0013 |
| 42 | API live on Render, real visitor address for rate limits |
| 43 | Job import on GitHub Actions, import lock fixed for Neon, run every 3 hours |
| 44 | Website live on Cloudflare, CORS and API address set |
| 45 | Hosting and HTTPS added to the Privacy Policy |
| 46 | CI: backend tests, undefined-name check, lint and build on every push |

Email alerts (a planned Day 29) were dropped on purpose: people do not open them, and no email service means less personal data.

---

## Project structure

```text
swipeX/
|-- backend/
|   |-- app/
|   |   |-- main.py                 App setup, routers, middleware
|   |   |-- models.py               All database tables
|   |   |-- security.py, deps.py    Tokens, passwords, roles
|   |   |-- ratelimit.py            Login, sign-up and reset limits, real visitor address
|   |   |-- errors.py, status.py    Error tracking, worker heartbeat
|   |   |-- storage.py              Resumes and photos from the database
|   |   |-- resume_tools.py         PDF reading, health score, match score
|   |   |-- ai.py                   AI helper (Groq)
|   |   |-- safety.py               Job and posting safety checks
|   |   |-- joblock.py              One import at a time
|   |   |-- routers/                One file per feature area
|   |   |-- importers/              Job boards, scheduler, sync, cleanup
|   |   `-- trust/                  Wikidata, website and domain checks, trust card
|   |-- alembic/versions/           Database migrations (0001 to 0013)
|   |-- tests/                      254 automated tests
|   |-- worker.py                   Background worker (Docker setup)
|   |-- run_scheduled.py            One importer run for GitHub Actions
|   |-- create_admin.py             Create or reset an admin account
|   |-- Dockerfile
|   `-- requirements.txt
|-- frontend/
|   |-- src/pages/                  Screens and sections
|   |-- src/index.css               Soft capsule theme
|   |-- public/_headers             Security headers for the live website
|   |-- wrangler.jsonc              Cloudflare settings
|   |-- nginx.conf                  Docker web server (serves files, forwards /api)
|   `-- Dockerfile
|-- extension/                      Chrome autofill extension
|-- .github/workflows/              tests.yml (CI) and import.yml (job importer)
|-- docs/schema.md                  Database diagram
|-- docker-compose.prod.yml         db + api + worker + web
|-- make-prod-env.ps1               Creates .env.prod with random secrets
|-- dc.ps1                          Short Docker command
|-- start-backend.ps1               Local database + backend
`-- start-frontend.ps1              Local website
```

---

## Run it locally

**You need:** Python 3.12, Node 22, Docker Desktop and Git. Commands are for Windows PowerShell.

```powershell
git clone https://github.com/narasimha4576/swipeX.git
Set-Location swipeX

# Backend
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # then open .env and fill it in (see Configuration)
Set-Location ..

.\start-backend.ps1                # starts the database in Docker, updates it, starts the API
```

In a second terminal:

```powershell
Set-Location swipeX
.\start-frontend.ps1               # website at http://localhost:5173
```

Create your first admin account:

```powershell
python backend\create_admin.py     # asks for an email and a password (also resets a forgotten one)
```

Helpful scripts (run from the project folder, with the virtual environment active):

| Script | What it does |
|---|---|
| `python backend\run_import.py` | Runs one job import now |
| `python backend\run_scheduled.py` | Runs one full scheduled run: import, cleanup, heartbeat |
| `python backend\check_boards.py` | Tests the job board sources |
| `python backend\seed_jobs.py` | Adds sample jobs |
| `python backend\test_ai.py` | Checks the AI connection |
| `python backend\pick_ai_model.py` | Finds a working free AI model |
| `python backend\check_alerts.py` | Runs the saved-search check by hand |
| `python backend\check_indexes.py` | Shows database indexes and query speed |
| `python backend\check_hosting.py "<connection string>"` | Checks a remote database before hosting |
| `python backend\move_files_to_db.py` | Copies old resume and photo files into the database |
| `python backend\worker.py` | Runs the background worker on its own |

### Chrome extension

1. Open `chrome://extensions` and switch on **Developer mode**.
2. Click **Load unpacked** and choose the `extension` folder.
3. On a job page, use **Review and autofill**, then **Fill the form**.

Orange outlines are filled by rules, purple by AI, and red dashed fields still need an answer. Questions about gender, race, disability, veteran status and pay are never auto-answered. For now the extension works with the local site only. Packaging it for the live site is Day 47.

---

## Run it with Docker (production style)

```powershell
.\make-prod-env.ps1               # creates .env.prod with random passwords (never committed)
.\dc.ps1 up -d --build            # builds and starts db, api, worker and web
.\dc.ps1 ps                       # all four should be healthy
.\dc.ps1 exec api python create_admin.py
```

Open **http://localhost:8080**. The website and the API share one address (`/api`).

| Command | Purpose |
|---|---|
| `.\dc.ps1 logs -f api worker` | Watch the logs |
| `.\dc.ps1 down` | Stop (keeps data) |
| `.\dc.ps1 up -d --build` | Apply code changes |
| `.\dc.ps1 down -v` | **Erase everything, including the database** |

---

## Configuration

Copy `backend/.env.example` to `backend/.env`. Never commit `.env` or `.env.prod`.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://user:password@host:port/database` (add `?sslmode=require` for Neon, and use the direct address, not the pooled one) |
| `SECRET_KEY` | Long random text, at least 32 characters (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Login lifetime, default 60 |
| `APP_ENV` | `production` hides `/docs` and enforces a strong secret key |
| `CORS_ORIGINS` | Allowed websites, comma separated. In production this replaces the localhost defaults, so put the live website address here (no slash at the end) |
| `TRUST_PROXY` | `true` behind Render. The real visitor address is read from `True-Client-IP`, then `CF-Connecting-IP`, then `X-Forwarded-For` |
| `ENABLE_HSTS` | `true` once the API is served over HTTPS without another layer adding it |
| `IMPORT_ENABLED` | Turn the job importer on or off |
| `IMPORT_INTERVAL_MINUTES` | How often the worker imports, default 15 |
| `IMPORT_ALL_JOBS` | `true` imports all jobs worldwide |
| `RUN_SCHEDULER_IN_API` | `false` when a separate worker or GitHub Actions runs the importer |
| `WORKER_FRESH_SECONDS` | How old the importer heartbeat may be before the System page says "Stopped?" (180 by default, 5400 on the live site) |
| `SKIP_RETENTION_DAYS` | Skipped jobs are forgotten after this many days (15) |
| `JOB_RETENTION_DAYS` | Closed imported jobs are deleted after this many days (60) |
| `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY` | AI provider (Groq is free) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRIES` | Optional extra job source |
| `TAVILY_API_KEY`, `YOUTUBE_API_KEY` | Optional company web search and videos |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Database connections (defaults 10 and 20, use 3 and 5 on free hosting) |
| `SLOW_QUERY_MS` | Warn about database queries slower than this (300) |
| `VITE_API_URL` | API address built into the website (set in `frontend/.env.production` for the live site) |

---

## API overview

Interactive documentation is at `/docs` while developing (it is hidden when `APP_ENV=production`).

| Area | Main endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `GET /auth/me`, `POST /auth/change-password`, `GET` and `POST /auth/recovery`, `POST /auth/forgot` |
| Profile | `GET` and `PUT /profile/me`, `/profile/experiences`, `/profile/educations`, `/profile/portfolio`, `/profile/photo`, `/profile/public`, public page `GET /public/profiles/{slug}` |
| Jobs | `GET /jobs`, `/jobs/{id}`, `/jobs-for-you`, `/job-countries`, `/jobs/{id}/match`, `/jobs/{id}/safety`, `POST /jobs/{id}/resume-tips` |
| Companies | `GET /companies/{id}/trust`, `/explore/search`, `/explore/company/{id}`, `/explore/web` |
| Swipes | `GET /swipes/deck`, `POST /swipes`, `DELETE /swipes/{job_id}`, `GET /swipes/skipped` |
| Applications | `POST /applications/apply`, `GET /applications`, `DELETE /applications/{id}`, `POST /applications/{id}/mark-applied` |
| Resumes | `POST /resumes`, `GET /resumes`, `GET /resumes/{id}/file`, `/resumes/{id}/analysis` |
| Autofill | `GET` and `PUT /autofill/details`, `GET /autofill/payload/{job_id}`, `POST /autofill/token`, `POST /autofill/answers` |
| Recruiter | `PUT /recruiter/company`, `/recruiter/jobs`, `/recruiter/jobs/{id}/applicants`, `PATCH /recruiter/applications/{id}/status`, `/recruiter/team` |
| Alerts | `/saved-searches`, `/notifications` |
| Account | `GET /account/export`, `POST /account/delete` |
| Feedback and help | `POST /feedback`, `POST /chat`, admin `GET /admin/feedback` |
| Admin | `/admin/users`, `/admin/users/{id}/detail`, `/admin/companies`, `/admin/overview`, `/admin/analytics`, `/admin/system`, `/admin/errors` |
| Health | `/health` (cheap, does not wake the database), `/health/db`, `/health/ready`, `/health/worker` |

---

## Security and privacy design

- **Passwords:** Argon2 hashes. Login, sign-up, password reset and feedback are rate limited, and unknown emails take the same time as real ones. Behind Render the real visitor address is used, so one person cannot block everyone.
- **Tokens:** signed JWTs with an expiry. The short-lived autofill token is refused everywhere except the autofill endpoint. A disabled account stops working immediately.
- **Your data only:** every endpoint checks ownership. Tests prove users, recruiters and companies cannot read each other's resumes, applications or notifications.
- **Admin sees the minimum:** account basics and counts only. No profiles, resumes or application details. Every admin look is written to an activity log.
- **Uploads:** PDFs only, real PDF header, 5 MB, at most 10 pages, no scripts or attachments, no password-locked files. Photos are re-encoded (this removes hidden data such as GPS).
- **Web protection:** security headers on the API and the website, a request size limit, a strict CORS list and a hidden API docs page in production. All traffic uses HTTPS.
- **Account control:** download all your data as a ZIP, or delete your account and everything personal in it.
- **Errors without leaks:** crash reports hide emails, tokens and long numbers, and are deleted after 30 days.
- **No email service:** nothing is emailed. Notifications live in the app, and password recovery uses one-time codes.
- **Secrets:** `.env` files are ignored by Git, and production secrets live only in the hosting dashboards.

---

## Testing and CI

```powershell
Set-Location backend
pytest                     # 254 tests, about 2.5 minutes

Set-Location ..\frontend
npm run lint               # should print nothing
npm run build              # production build
```

- On every push, GitHub Actions runs the backend tests on a temporary PostgreSQL, a check for undefined names, the frontend lint and the production build.
- Tests run on a separate database, `swipex_test`, that is rebuilt from the models on every run. Your real data is never touched.
- The tests cover sign-up and login, roles, profiles, jobs and filters, swiping and applying, recruiter and team flows, notifications, privacy rules, uploads, rate limits, the admin pages, account export and delete, recovery codes, error tracking and database file storage.

---

## Hosting plan (free tier)

```mermaid
flowchart LR
  GH["GitHub repository"] --> R["Render: Docker API"]
  GH --> CF["Cloudflare: website"]
  GH --> GA["GitHub Actions: import every 3 hours, CI"]
  R --> N[("Neon: PostgreSQL")]
  GA --> N
  CF -->|"calls the API"| R
  UP["UptimeRobot (planned)"] -->|"ping /health"| R
```

| Part | Where | Why |
|---|---|---|
| Website | Cloudflare (static assets), `swipex.jobslist.workers.dev` | Free, never sleeps, free HTTPS |
| API | Render free web service (Docker, Singapore) | Runs the existing Dockerfile, free HTTPS |
| Database | Neon free (direct connection, Singapore) | Not deleted after 30 days like Render's free database |
| Job import | GitHub Actions, every 3 hours | A sleeping API cannot run a scheduler |
| Uptime alerts | UptimeRobot pinging `/health` (planned, Day 48) | `/health` does not wake the database |

Free-tier facts that shape the design: the API sleeps after 15 idle minutes, has 512 MB memory and no disk. Neon allows 1 GB of data and 100 compute-hours a month, and sleeps after 5 idle minutes. A full import takes about 11 minutes, which is why it runs every 3 hours and not every hour. Files live in the database, and the direct connection address is used because the pooled one breaks the import lock.

---

## Roadmap: what's left

| Day | Task | Status |
|---|---|---|
| 1 to 40 | Core product, AI features, extension, security, privacy, admin tools, Docker, hosting chosen | Done |
| 41 | Files stored in the database, old-job cleanup, migration 0013, 254 tests passing | Done |
| 42 | API live on Render, real visitor address for rate limits | Done |
| 43 | Importer on GitHub Actions (every 3 hours), lock fixed for Neon | Done |
| 44 | Website live on Cloudflare, CORS and API address set | Done |
| 45 | Hosting and HTTPS added to the Privacy Policy, full walkthrough of the live site | Verify |
| 46 | CI: tests, undefined-name check, lint and build on every push | Verify |
| 47 | Package the Chrome extension for the live site | Next |
| 48 | Backups, keep-alive pings and uptime alerts | Planned |
| 49 to 50 | Beta with 10 to 20 real users, fix the top issues | Planned |
| 51 | Legal check of each job source's terms, attribution links | Planned |
| 52 to 53 | Landing page and demo video | Planned |
| 54 | Final review, update the resume to "deployed" | Planned |

### Later ideas

- **A. Public profiles** with shareable links (basic version exists).
- **B. Network:** follow, connect, feed and posts.
- **C. Messaging.**
- **D. Recruiter talent search**, company pages, job promotion.
- **E. Semantic search**, resume builder, interview practice.
- **F. Play Store app** (PWA wrapped with Capacitor or a Trusted Web Activity), landing page and premium plans.

---

## Known limits

- **Free hosting sleeps.** The first request after a quiet period is slow.
- **Neon compute hours.** The free plan allows 100 hours a month, so the importer runs every 3 hours.
- **Rate limits live in memory.** They reset when the server restarts. A second layer is planned at the web server.
- **Old logins last up to 60 minutes after a password change,** until their token expires.
- **Recovery codes are the only way back in.** Someone who forgot their password and never saved codes cannot recover that account. Admins cannot reset other people's passwords, to protect privacy.
- **The autofill extension** works only with the local site until it is packaged for the live one (Day 47).
- **The Docker database uses a superuser account.** A least-privilege role is a future hardening step.
- **Legal text is a starter draft.** Have the Privacy Policy and Terms reviewed before many real users sign up.

---

## Author

Built by **V Lakshmi Narasimha** as an end-to-end portfolio project: backend, frontend, database, AI features, tests, security and deployment.
GitHub: [@narasimha4576](https://github.com/narasimha4576)

License: not chosen yet (all rights reserved until one is added).