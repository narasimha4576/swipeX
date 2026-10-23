# SwipeX

Swipe-based intelligent job discovery and career assistance platform.

**Stack:** FastAPI, React, PostgreSQL, Docker

## Database Design

```mermaid
erDiagram
    USERS ||--o| PROFILES : has
    USERS ||--o{ RESUMES : uploads
    USERS ||--o{ SWIPES : makes
    USERS ||--o{ APPLICATIONS : submits
    COMPANIES ||--o{ JOBS : posts
    JOBS ||--o{ SWIPES : receives
    JOBS ||--o{ APPLICATIONS : receives
    RESUMES ||--o{ APPLICATIONS : used_in
```