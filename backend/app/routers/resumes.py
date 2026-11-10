import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Application, Resume, User
from app.resume_tools import read_pdf_bytes
from app.storage import pdf_response, resume_bytes
from app.upload_checks import validate_pdf
from app.schemas import ResumeOut

router = APIRouter(prefix="/resumes", tags=["resumes"])
seeker_only = require_roles("job_seeker")

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploads" / "resumes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 5 * 1024 * 1024
MAX_RESUMES = 5


def get_own_resume(db: Session, user: User, resume_id: int) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    stmt = (
        select(Resume)
        .where(Resume.user_id == user.id)
        .order_by(Resume.is_default.desc(), Resume.id.desc())
    )
    return db.scalars(stmt).all()


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(
    version_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    name = version_name.strip()
    if not 1 <= len(name) <= 120:
        raise HTTPException(status_code=400, detail="Give the resume a name (up to 120 characters)")

    count = db.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == user.id)
    )
    if count >= MAX_RESUMES:
        raise HTTPException(status_code=400, detail=f"You can keep up to {MAX_RESUMES} resumes")

    content = file.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is too large (maximum 5 MB)")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")

    validate_pdf(content)
    filename = f"{uuid.uuid4().hex}.pdf"
    parsed_text, _pages = read_pdf_bytes(content)

    resume = Resume(
        user_id=user.id,
        version_name=name,
        file_path=filename,
        file_data=content,
        parsed_text=parsed_text or None,
        is_default=(count == 0),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/{resume_id}/file")
def download_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    resume = get_own_resume(db, user, resume_id)
    content = resume_bytes(resume, UPLOAD_DIR)
    if content is None:
        raise HTTPException(status_code=404, detail="File is missing on the server")
    return pdf_response(content, resume.version_name)


@router.patch("/{resume_id}/default", response_model=ResumeOut)
def make_default(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    resume = get_own_resume(db, user, resume_id)
    for other in db.scalars(select(Resume).where(Resume.user_id == user.id)):
        other.is_default = other.id == resume.id
    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    resume = get_own_resume(db, user, resume_id)
    used = db.scalar(
        select(func.count()).select_from(Application).where(Application.resume_id == resume.id)
    )
    if used:
        raise HTTPException(
            status_code=400,
            detail="This resume was used in an application and cannot be deleted",
        )

    was_default = resume.is_default
    path = UPLOAD_DIR / resume.file_path
    db.delete(resume)
    db.commit()
    path.unlink(missing_ok=True)

    if was_default:
        next_resume = db.scalar(
            select(Resume).where(Resume.user_id == user.id).order_by(Resume.id)
        )
        if next_resume is not None:
            next_resume.is_default = True
            db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)