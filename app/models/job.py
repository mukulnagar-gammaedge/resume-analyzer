import uuid
from app.db.base import Base
from sqlalchemy import Column, String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_path = Column(String, nullable=False)
    job_description = Column(Text, nullable=True)

    extracted_resume_json = Column(JSON, nullable=True)
    extracted_jd_json = Column(JSON, nullable=True)

    overall_score = Column(Float, nullable=True)
    match_percentage = Column(Float, nullable=True)

    missing_skills = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)

    analysis_summary = Column(Text, nullable=True)

    status = Column(String, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
