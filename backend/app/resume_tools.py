import re
from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.skills import extract_skills

MAX_CHARS = 60000
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
NUMBERS = re.compile(r"\d+\s*%|\b\d{2,}\b")

SECTION_PATTERNS = {
    "summary": r"^(professional\s+)?(summary|objective|profile|about( me)?)\b",
    "education": r"^(education|academic)\b",
    "experience": r"^(work\s+|professional\s+)?(experience|employment|internships?)\b",
    "projects": r"^(personal\s+|academic\s+)?projects?\b",
    "skills": r"^(technical\s+|key\s+)?skills\b|^core competencies",
    "certifications": r"^(certifications?|achievements|awards)\b",
}


def read_pdf(path: Path) -> tuple[str, int]:
    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:6])
    except Exception:
        return "", 0
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS], pages


def page_count(path: Path) -> int:
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0


def detect_sections(text: str) -> dict[str, bool]:
    lines = [line.strip().lower() for line in text.splitlines() if 0 < len(line.strip()) < 40]
    return {
        name: any(re.match(pattern, line) for line in lines)
        for name, pattern in SECTION_PATTERNS.items()
    }


def contact_info(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "email": bool(EMAIL.search(text)),
        "phone": bool(PHONE.search(text)),
        "linkedin": "linkedin.com" in lowered,
        "github": "github.com" in lowered,
    }


def analyze_resume(text: str, pages: int) -> dict:
    words = len(re.findall(r"\b\w+\b", text))
    readable = len(text) >= 200
    sections = detect_sections(text)
    contact = contact_info(text)
    skills = extract_skills(text)

    score = 100
    tips: list[str] = []
    if not readable:
        score -= 60
        tips.append(
            "SwipeX could hardly read any text in this PDF. It may be a scan or a picture. "
            "Export a text PDF from Word or Google Docs, because ATS systems cannot read images."
        )
    if not contact["email"]:
        score -= 10
        tips.append("Add your email address near the top.")
    if not contact["phone"]:
        score -= 5
        tips.append("Add a phone number.")
    if not sections["education"]:
        score -= 10
        tips.append('Add a clear "Education" heading.')
    if not sections["skills"]:
        score -= 10
        tips.append('Add a "Skills" section with the tools you really use.')
    if not (sections["experience"] or sections["projects"]):
        score -= 10
        tips.append('Add "Experience" or "Projects" that show what you built.')
    if readable and words < 150:
        score -= 15
        tips.append("The resume is very short. Add projects, internships or achievements.")
    if words > 1100:
        score -= 10
        tips.append("The resume is long. Freshers usually fit one page, about 400 to 700 words.")
    if pages > 2:
        score -= 10
        tips.append("It has more than 2 pages. Try to keep it to 1 page.")
    if readable and not NUMBERS.search(text):
        score -= 5
        tips.append("Add numbers to show impact, for example improved accuracy by 12 percent.")
    if readable and len(skills) < 5:
        tips.append("Few skills were found. Name tools and technologies, for example Python, SQL, Docker.")
    if not tips:
        tips.append("This resume looks clean for ATS systems. Next, tailor it to each job.")

    return {
        "pages": pages,
        "words": words,
        "readable": readable,
        "score": max(0, min(100, score)),
        "skills": skills,
        "sections": sections,
        "contact": contact,
        "tips": tips,
    }


def text_similarity(resume_text: str, job_text: str) -> float:
    if not resume_text.strip() or not job_text.strip():
        return 0.0
    try:
        matrix = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        ).fit_transform([resume_text, job_text])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        return 0.0


def label_for(score: int) -> str:
    if score >= 75:
        return "Strong match"
    if score >= 50:
        return "Good match"
    if score >= 25:
        return "Partial match"
    return "Low match"


def match_job(resume_text: str, job_skills: list[str], job_title: str, job_description: str) -> dict:
    have = {s.lower() for s in extract_skills(resume_text)}
    matched = [s for s in job_skills if s.lower() in have]
    missing = [s for s in job_skills if s.lower() not in have]

    similarity = text_similarity(resume_text, f"{job_title}\n{job_description}")
    text_score = min(1.0, similarity / 0.35)
    if job_skills:
        raw = 0.65 * (len(matched) / len(job_skills)) + 0.35 * text_score
    else:
        raw = text_score
    score = max(0, min(100, round(raw * 100)))

    tips: list[str] = []
    if len(resume_text) < 200:
        tips.append("Your resume text could not be read, so this score is not reliable. Use a text PDF.")
    if missing:
        tips.append(
            "Your resume does not mention: " + ", ".join(missing[:8])
            + ". Add them only if you really have those skills."
        )
    if not job_skills:
        tips.append("This posting lists no skills, so the score is based on the wording only.")
    if score >= 75:
        tips.append("Strong match. Tailor your summary to this role's wording and apply.")
    elif score < 50:
        tips.append("Try a resume version closer to this role, or build the missing skills first.")

    return {
        "score": score,
        "label": label_for(score),
        "matched_skills": matched,
        "missing_skills": missing,
        "text_match_percent": round(similarity * 100),
        "tips": tips,
    }

def read_pdf_bytes(content: bytes) -> tuple[str, int]:
    import io

    try:
        reader = PdfReader(io.BytesIO(content))
        pages = len(reader.pages)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:6])
    except Exception:
        return "", 0
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS], pages


def page_count_bytes(content: bytes) -> int:
    import io

    try:
        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:
        return 0