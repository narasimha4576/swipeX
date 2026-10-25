<h1 align="center">SwipeX</h1>

<p align="center">
  <b>Swipe-based intelligent job discovery and career assistance platform</b><br/>
  Swipe through jobs, save the ones you like, apply with the right resume, and track every application in one place.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Status-In%20development-orange" alt="Status" />
</p>

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [How it works](#how-it-works)
- [Database design](#database-design)
- [Roles and permissions](#roles-and-permissions)
- [API overview](#api-overview)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Design notes](#design-notes)
- [Security](#security)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Overview

Finding a job usually means scrolling through long lists and filling the same forms again and again. **SwipeX** makes it feel like using a modern phone app:

- **Job seekers** swipe through job cards, save the ones they like, and apply with the resume that fits best.
- **Recruiters** create a company profile, post jobs, and see them go live instantly.
- **Admins** manage users and keep the platform healthy.

The app has an iPhone-style glassmorphism design: a colourful gradient wallpaper, frosted glass cards, and a floating bottom tab bar.

> The sample companies and jobs in this project are made up. They exist only so the app has data to show during development.

---

## Features

### Job seekers
- [x] Sign up, log in, secure sessions with JWT
- [x] **Discover**: swipe cards (right = save, left = skip, undo, keyboard arrows)
- [x] **Jobs**: search, quick filters (MNC, Startup, New startup, Remote, Fresher-friendly, Low competition, Last 7 days, Internships), advanced filters (location, skill, minimum salary, experience level) and sorting
- [x] **Competition level** on every job (Low, Medium, High) based on applicant count
- [x] **Profile**: headline, location, experience, skill tags, about text, profile strength meter
- [x] **Experience history** and **portfolio links**
- [x] **Resumes**: upload up to 5 PDF versions, choose a default, view or delete
- [x] **Apply** with a chosen resume and track status in **Applications** (Saved, Applied, Shortlisted, Interview, Rejected)

### Recruiters
- [x] Create and edit a company profile (MNC, startup or newly founded startup)
- [x] Post jobs (type, level, salary range, skills, remote option)
- [x] Close and reopen postings
- [x] Review applicants (profile, skills, experience, portfolio, resume PDF) and move them to shortlisted, interview or rejected

### Admins
- [x] See all users
- [x] Enable or disable accounts (disabled users cannot log in)

---

## Architecture

```mermaid
flowchart LR
    subgraph Client["Browser"]
        UI["React + Vite<br/>iPhone-style glass UI"]
    end

    subgraph Server["Backend (FastAPI)"]
        API["REST API<br/>9 routers"]
        AUTH["JWT auth<br/>and role checks"]
        ORM["SQLAlchemy ORM"]
    end

    subgraph Docker["Docker Compose"]
        PG[("PostgreSQL 16")]
    end

    FS[("Resume PDFs<br/>backend/uploads")]

    UI -- "JSON over HTTP<br/>Bearer token" --> API
    API --> AUTH
    API --> ORM
    ORM --> PG
    API --> FS
```

The React app talks to the FastAPI backend with JSON requests. Every protected request carries a JWT token. The backend checks the token and the user's role, reads or writes PostgreSQL through SQLAlchemy, and stores uploaded resumes on disk.

---

## How it works

### Sign up and log in

```mermaid
sequenceDiagram
    participant B as Browser
    participant API as FastAPI
    participant DB as PostgreSQL

    B->>API: POST /auth/register (email, password, role)
    API->>DB: Save user with argon2 password hash
    B->>API: POST /auth/login (email, password)
    API->>DB: Load user and verify password hash
    API-->>B: JWT access token (expires in 60 minutes)
    B->>API: GET /auth/me with Authorization header
    API-->>B: Current user and role
    Note over B,API: Every protected route checks the token and the role
```

### From a posted job to an application

```mermaid
sequenceDiagram
    actor R as Recruiter
    actor S as Job seeker
    participant App as SwipeX

    R->>App: Create company profile
    R->>App: Post a job
    App-->>S: Job appears in Jobs and Discover
    S->>App: Swipe right (save)
    S->>App: Apply with a chosen resume
    App-->>App: Applicant count goes up
    App-->>R: Applicants with profile and resume
    R->>App: Shortlist, interview or reject
    App-->>S: New status shows in Applications
```

### Swiping

```mermaid
flowchart TD
    A["Deck: active jobs you have not swiped yet"] --> B{"Swipe"}
    B -- "Right" --> C["Saved application created"]
    B -- "Left" --> D["Skipped, never shown again"]
    C --> E["Applications tab: Saved"]
    E --> F["Apply with a resume"]
    E --> G["Remove (counts as skipped)"]
    F --> H["Applications tab: Applied"]
    B -. "Undo" .-> A
```

### Application status

```mermaid
stateDiagram-v2
    [*] --> Saved: swipe right
    Saved --> Applied: apply with resume
    Saved --> [*]: remove
    Applied --> Shortlisted
    Applied --> Rejected
    Shortlisted --> Interview
    Shortlisted --> Rejected
    Interview --> Rejected
```

The job seeker moves a job from Saved to Applied. The later steps (Shortlisted, Interview, Rejected) are decided by the recruiter and are shown to the job seeker in the Applications tab.

---

## Database design

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has one"
    USERS ||--o{ EXPERIENCES : lists
    USERS ||--o{ PORTFOLIO_ITEMS : shares
    USERS ||--o{ RESUMES : uploads
    USERS ||--o{ SWIPES : makes
    USERS ||--o{ APPLICATIONS : submits
    USERS ||--o| RECRUITER_PROFILES : "recruiter link"
    COMPANIES ||--o{ RECRUITER_PROFILES : "belongs to"
    COMPANIES ||--o{ JOBS : posts
    JOBS ||--o{ SWIPES : receives
    JOBS ||--o{ APPLICATIONS : receives
    RESUMES ||--o{ APPLICATIONS : "used in"

    USERS {
        int id PK
        string email UK
        string password_hash
        string full_name
        string role "job_seeker, recruiter or admin"
        bool is_active
    }
    PROFILES {
        int id PK
        int user_id FK
        string headline
        string location
        float experience_years
        json skills
        text bio
    }
    EXPERIENCES {
        int id PK
        int user_id FK
        string company
        string title
        int start_year
        int end_year "empty means current"
    }
    PORTFOLIO_ITEMS {
        int id PK
        int user_id FK
        string title
        string url
    }
    RESUMES {
        int id PK
        int user_id FK
        string version_name
        string file_path
        bool is_default
    }
    COMPANIES {
        int id PK
        string name UK
        string company_type "mnc, startup or new_startup"
        string location
        int founded_year
    }
    RECRUITER_PROFILES {
        int id PK
        int user_id FK
        int company_id FK
    }
    JOBS {
        int id PK
        int company_id FK
        int posted_by FK
        string title
        text description
        string job_type "full_time or internship"
        string experience_level
        float salary_min_lpa
        float salary_max_lpa
        json skills
        int applicant_count
        bool is_active
    }
    SWIPES {
        int id PK
        int user_id FK
        int job_id FK
        string direction "left or right"
    }
    APPLICATIONS {
        int id PK
        int user_id FK
        int job_id FK
        int resume_id FK
        string status "saved, applied, shortlisted, interview or rejected"
        float ats_score "planned"
    }
```

One swipe and one application are allowed per user and job, so nobody can swipe or apply to the same job twice.

---

## Roles and permissions

| Action | Job seeker | Recruiter | Admin |
|---|:---:|:---:|:---:|
| Browse, search and filter jobs | Yes | Yes | Yes |
| Swipe, save and apply | Yes | No | No |
| Manage profile, experience, portfolio and resumes | Yes | No | No |
| Create a company and post or close jobs | No | Yes | No |
| Review applicants and update their status | No | Yes | No |
| List users and enable or disable accounts | No | No | Yes |

Only job seekers and recruiters can sign up on their own. The first admin is created with a script.

---

## API overview

Interactive API docs are available at `http://127.0.0.1:8000/docs` while the backend is running.

| Area | Endpoints |
|---|---|
| Health | `GET /health`, `GET /health/db` |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Admin | `GET /admin/users`, `PATCH /admin/users/{id}/active` |
| Profile | `GET /profile/me`, `PUT /profile/me` |
| Experience | `GET /profile/experiences`, `POST /profile/experiences`, `DELETE /profile/experiences/{id}` |
| Portfolio | `GET /profile/portfolio`, `POST /profile/portfolio`, `DELETE /profile/portfolio/{id}` |
| Resumes | `GET /resumes`, `POST /resumes`, `GET /resumes/{id}/file`, `PATCH /resumes/{id}/default`, `DELETE /resumes/{id}` |
| Jobs | `GET /jobs` (search, filters, sort, pages), `GET /jobs/{id}`, `GET /companies` |
| Swipes | `GET /swipes/deck`, `POST /swipes`, `DELETE /swipes/{job_id}` (undo) |
| Applications | `GET /applications`, `POST /applications/apply`, `DELETE /applications/{id}` (saved only) |
| Recruiter | `GET /recruiter/company`, `PUT /recruiter/company`, `GET /recruiter/jobs`, `POST /recruiter/jobs`, `PATCH /recruiter/jobs/{id}/active`, `GET /recruiter/jobs/{id}/applicants`, `PATCH /recruiter/applications/{id}/status`, `GET /recruiter/applications/{id}/resume` |

`GET /jobs` filters: `q`, `company_type`, `job_type`, `experience_level`, `remote`, `location`, `skill`, `min_salary`, `max_age_days`, `fresher_friendly`, `low_competition`, `sort`, `page`, `page_size`.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), React Router, Axios, Framer Motion, plain CSS |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Auth | JWT (PyJWT), argon2 password hashing (pwdlib) |
| Database | PostgreSQL 16 in Docker |
| Files | Resume PDFs stored in `backend/uploads` (not in Git) |
| Tooling | Docker Compose, Git and GitHub, PowerShell start scripts |

---

## Project structure

```text
swipeX/
|-- backend/
|   |-- app/
|   |   |-- main.py            App setup, CORS, routers
|   |   |-- database.py        Database connection
|   |   |-- models.py          Database tables
|   |   |-- schemas.py         Request and response rules
|   |   |-- security.py        Password hashing and JWT
|   |   |-- deps.py            Current user and role checks
|   |   `-- routers/
|   |       |-- auth.py            Sign up, log in, current user
|   |       |-- admin.py           User management
|   |       |-- profile.py         Job seeker profile
|   |       |-- profile_items.py   Experience and portfolio
|   |       |-- resumes.py         Resume upload and files
|   |       |-- jobs.py            Job list, search, filters, companies
|   |       |-- swipes.py          Swipe deck, save, skip, undo
|   |       |-- applications.py    Apply and track applications
|   |       `-- recruiter.py       Company and job postings
|   |-- create_admin.py        Create or reset an admin account
|   |-- seed_jobs.py           Sample companies and jobs
|   |-- requirements.txt
|   `-- .env.example
|-- frontend/
|   `-- src/
|       |-- main.jsx, App.jsx, api.js, auth.jsx, jobUtils.js, index.css
|       `-- pages/
|           |-- AuthPage.jsx          Log in and sign up
|           |-- Discover.jsx          Swipe cards
|           |-- Jobs.jsx              Search and filters
|           |-- Applications.jsx      Application tracking
|           |-- Profile.jsx, ResumeSection.jsx,
|           |   ExperienceSection.jsx, PortfolioSection.jsx
|           |-- Workspace.jsx         Recruiter workspace
|           |-- MyPostings.jsx        Recruiter job list
|           |-- ApplicantsPanel.jsx   Review applicants
|           `-- AdminUsers.jsx        Admin users table
|-- docs/
|   `-- schema.md
|-- compose.yml                PostgreSQL container
|-- start-backend.ps1          Starts the database and the API
|-- start-frontend.ps1         Starts the website
`-- README.md
```

---

## Getting started

**You need:** Git, Python 3.12 or newer, Node.js (LTS) and Docker Desktop.

The commands below are for Windows PowerShell. On macOS or Linux, use `source .venv/bin/activate` instead of the activate line, and `cp` instead of `Copy-Item`.

### 1. Get the code and start the database
```powershell
git clone https://github.com/narasimha4576/swipeX.git
cd swipeX
docker compose up -d
```

### 2. Set up the backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Open `backend/.env` and replace the `SECRET_KEY` placeholder with a long random string. You can generate one with:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Then add sample data, create your first admin, and start the API:
```powershell
python seed_jobs.py
python create_admin.py
uvicorn app.main:app --reload
```

### 3. Start the frontend (in a new terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**, then sign up as a job seeker or a recruiter.

### Shortcut
Once everything is installed, two commands from the project folder start everything:
```powershell
.\start-backend.ps1
.\start-frontend.ps1
```
Run each one in its own terminal. Docker Desktop must be running first.

---

## Configuration

Backend settings live in `backend/.env` (copy them from `backend/.env.example`):

| Variable | Meaning | Example |
|---|---|---|
| `DATABASE_URL` | Connection string for PostgreSQL | `postgresql+psycopg://swipex:swipex_pass@localhost:5433/swipex` |
| `SECRET_KEY` | Secret used to sign login tokens | a long random string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login token lasts | `60` |

The frontend uses `http://127.0.0.1:8000` as the API address. To change it, set `VITE_API_URL`.

The database listens on port **5433** on your machine, so it does not clash with a PostgreSQL that may already use 5432.

---

## Design notes

**Look and feel.** iPhone-style glassmorphism: a slowly moving gradient wallpaper, frosted glass cards, a floating bottom tab bar with icons, large bold page titles, and company logo tiles on job cards.

**Competition level.** A simple rule based on the number of applicants:

| Applicants | Level |
|---|---|
| Fewer than 60 | Low |
| 60 to 199 | Medium |
| 200 or more | High |

**Swipe meaning.** Swipe right saves a job (it is added to Applications as "Saved"). Swipe left skips it. Applying is a separate, deliberate step where you choose a resume.

---

## Security

- Passwords are never stored. Only an **argon2 hash** is saved.
- Login tokens are **JWTs that expire** (60 minutes by default) and are signed with a secret from `.env`.
- Every protected route checks the **role**. Users can only read or change **their own** data (profile, resumes, swipes, applications, postings).
- Login errors use the same message for a wrong email and a wrong password.
- Uploaded files must be **real PDFs** (checked by content, not only by name) and at most **5 MB**.
- `.env` files and `backend/uploads/` are **ignored by Git**.
- Disabled accounts cannot log in, and their old tokens stop working.

---

## Roadmap

**Done**
- [x] Project setup, Docker PostgreSQL, SQLAlchemy models
- [x] Authentication, roles, admin user management
- [x] Job seeker profile, experience, portfolio and resume upload
- [x] Jobs list with search, filters, sorting and competition level
- [x] Swipe discovery with save, skip and undo
- [x] Apply with a resume and application tracking
- [x] Recruiter company profile and job posting
- [x] iPhone-style glassmorphism interface
- [x] Recruiters review applicants (shortlist, interview, reject)

**In progress**
- [ ] Resume parsing and ATS scoring

**Next**
- [ ] Application timeline and small clean-ups (apply and save buttons on the Jobs list, company pages)
- [ ] Missing skills and keywords, with AI improvement suggestions
- [ ] Personalised recommendations and match percentages
- [ ] Notifications (new jobs, status changes)
- [ ] Analytics dashboards (applications, resume performance, skill gaps)
- [ ] Company and startup pages
- [ ] Import real jobs from public job APIs with "apply" links
- [ ] Automated tests, GitHub Actions CI, cloud deployment with Docker

---

## Author

Built by **Narasimha** as a hands-on full-stack and AI project.
GitHub: [@narasimha4576](https://github.com/narasimha4576)