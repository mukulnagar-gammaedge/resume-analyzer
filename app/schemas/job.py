from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional

class AnalyzeResponse(BaseModel):
    job_id: UUID
    status: str

class ResultResponse(BaseModel):
    status: str
    overall_score: Optional[float]
    match_percentage: Optional[float]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    missing_skills: Optional[List[str]]
    analysis_summary: Optional[str]
