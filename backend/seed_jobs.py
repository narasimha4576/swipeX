import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app import models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.models import Company, Job

random.seed(42)

COMPANIES = [
    ("Vertex Global Solutions", "mnc", "Bengaluru", 1998),
    ("Meridian Technologies", "mnc", "Hyderabad", 2003),
    ("Altura Systems", "mnc", "Pune", 2001),
    ("Paperboat Labs", "startup", "Bengaluru", 2019),
    ("Kiwi Analytics", "startup", "Chennai", 2020),
    ("Lumen AI", "startup", "Bengaluru", 2021),
    ("Sprout Health Tech", "new_startup", "Hyderabad", 2025),
    ("Nova Loop", "new_startup", "Bengaluru", 2025),
]

TEMPLATES = [
    {"title": "Machine Learning Engineer", "level": "fresher", "type": "full_time", "salary": (6, 10),
     "skills": ["Python", "PyTorch", "scikit-learn", "SQL"]},
    {"title": "Generative AI Developer", "level": "fresher", "type": "full_time", "salary": (7, 12),
     "skills": ["Python", "LLMs", "LangChain", "FastAPI", "RAG"]},
    {"title": "Data Analyst", "level": "fresher", "type": "full_time", "salary": (4, 7),
     "skills": ["SQL", "Excel", "Power BI", "Python"]},
    {"title": "AI Engineer", "level": "junior", "type": "full_time", "salary": (10, 18),
     "skills": ["Python", "LLM APIs", "Docker", "AWS"]},
    {"title": "Backend Developer (Python)", "level": "fresher", "type": "full_time", "salary": (5, 9),
     "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]},
    {"title": "Full Stack Developer", "level": "junior", "type": "full_time", "salary": (8, 15),
     "skills": ["React", "Node.js", "PostgreSQL", "REST APIs"]},
    {"title": "Data Scientist", "level": "mid", "type": "full_time", "salary": (15, 25),
     "skills": ["Python", "Machine Learning", "Statistics", "SQL"]},
    {"title": "MLOps Engineer", "level": "mid", "type": "full_time", "salary": (18, 30),
     "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Python"]},
    {"title": "Frontend Developer (React)", "level": "fresher", "type": "full_time", "salary": (4, 8),
     "skills": ["React", "JavaScript", "CSS", "Git"]},
    {"title": "AI/ML Intern", "level": "fresher", "type": "internship", "salary": (2.4, 4.8),
     "skills": ["Python", "Machine Learning", "NumPy", "Pandas"]},
    {"title": "Data Engineer", "level": "junior", "type": "full_time", "salary": (10, 18),
     "skills": ["Python", "SQL", "Spark", "Airflow"]},
    {"title": "NLP Engineer", "level": "junior", "type": "full_time", "salary": (12, 22),
     "skills": ["Python", "spaCy", "Transformers", "PyTorch"]},
]


def describe(company, template):
    skills = ", ".join(template["skills"][:3])
    text = (
        f"{company.name} is looking for a {template['title']}. "
        f"You will build and ship features using {skills} and work closely with a small, friendly team. "
    )
    if template["level"] == "fresher":
        text += "Freshers with strong projects are welcome to apply."
    else:
        text += "Hands-on experience with the listed tools is expected."
    return text


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Job)) > 0:
            print("Jobs already exist. Nothing to do.")
            return

        companies = []
        for name, ctype, city, year in COMPANIES:
            company = db.scalar(select(Company).where(Company.name == name))
            if company is None:
                company = Company(
                    name=name,
                    company_type=ctype,
                    location=city,
                    website="https://example.com",
                    founded_year=year,
                )
                db.add(company)
            companies.append(company)
        db.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        created = 0
        for template in TEMPLATES:
            for _ in range(2):
                company = random.choice(companies)
                hours_ago = random.randint(1, 14 * 24)
                remote = random.random() < 0.25
                low, high = template["salary"]
                bump = 0 if template["type"] == "internship" else random.choice([0, 0, 1, 2])
                db.add(
                    Job(
                        company_id=company.id,
                        title=template["title"],
                        description=describe(company, template),
                        location="Remote" if remote else company.location,
                        is_remote=remote,
                        job_type=template["type"],
                        experience_level=template["level"],
                        salary_min_lpa=low + bump,
                        salary_max_lpa=high + bump,
                        skills=template["skills"],
                        applicant_count=int(hours_ago / 24 * random.randint(5, 40))
                        + random.randint(0, 15),
                        created_at=now - timedelta(hours=hours_ago),
                    )
                )
                created += 1
        db.commit()
        print(f"Added {len(companies)} companies and {created} jobs.")


if __name__ == "__main__":
    main()