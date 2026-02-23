import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.job import Job
from app.schemas.job import AnalyzeResponse, ResultResponse
from app.tasks.analyze_task import process_resume
from app.core.config import settings
import os

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    if not resume.filename.endswith(".pdf"):
        raise ValueError("Only PDF allowed")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    job_id = uuid.uuid4()
    file_path = f"{settings.UPLOAD_DIR}/{job_id}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    job = Job(
        id=job_id,
        resume_path=file_path,
        job_description=job_description,
        status="pending"
    )

    db.add(job)
    await db.commit()

    process_resume.delay(str(job_id))

    return {"job_id": job_id, "status": "pending"}

@router.get("/result/{job_id}", response_model=ResultResponse)
async def get_result(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)

    return ResultResponse(
        status=job.status,
        overall_score=job.overall_score,
        match_percentage=job.match_percentage,
        strengths=job.strengths,
        weaknesses=job.weaknesses,
        missing_skills=job.missing_skills,
        analysis_summary=job.analysis_summary
    )
