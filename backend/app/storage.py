from pathlib import Path
from urllib.parse import quote

from fastapi import Response


def resume_bytes(resume, upload_dir: Path):
    """The PDF of a resume: from the database, or (for older resumes) from the disk. None if missing."""
    if resume.file_data:
        return bytes(resume.file_data)
    path = upload_dir / resume.file_path
    return path.read_bytes() if path.is_file() else None


def photo_bytes(profile, photo_dir: Path):
    """The profile photo: from the database, or (for older photos) from the disk. None if missing."""
    if profile is None or not profile.photo_path:
        return None
    if profile.photo_data:
        return bytes(profile.photo_data)
    path = photo_dir / profile.photo_path
    return path.read_bytes() if path.is_file() else None


def pdf_response(content: bytes, name: str) -> Response:
    disposition = "attachment; filename*=utf-8''" + quote(f"{name}.pdf")
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": disposition})