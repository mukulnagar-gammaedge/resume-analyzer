from app.core.celery_app import celery
from app.db.session import sync_engine
from sqlalchemy.orm import Session
from app.models.job import Job

from app.services.pdf_service import extract_text_from_pdf
from app.services.llm_service import (
    extract_resume_structured,
    extract_jd_structured,
    generate_qualitative_analysis
)
from app.services.matching_service import compute_skill_matching
from app.services.scoring_service import compute_final_score

import traceback


@celery.task(name="app.tasks.analyze_task.process_resume")
def process_resume(job_id: str):
    print(f"[TASK STARTED] Processing job: {job_id}")

    with Session(sync_engine) as db:
        job = db.get(Job, job_id)

        if not job:
            print(f"[ERROR] Job {job_id} not found in DB.")
            return

        try:
            # -------------------------------------------------
            # 1️⃣ Update Status → processing
            # -------------------------------------------------
            job.status = "processing"
            db.commit()

            # -------------------------------------------------
            # 2️⃣ Extract Resume Text
            # -------------------------------------------------
            print("[STEP] Extracting resume text...")
            resume_text = extract_text_from_pdf(job.resume_path)

            # -------------------------------------------------
            # 3️⃣ Extract Structured Resume Data
            # -------------------------------------------------
            print("[STEP] Extracting structured resume data...")
            resume_data = extract_resume_structured(resume_text)
            job.extracted_resume_json = resume_data

            # -------------------------------------------------
            # 4️⃣ Initialize scoring variables
            # -------------------------------------------------
            match_percentage = 0
            experience_score = 0
            project_score = 60  # deterministic placeholder
            optional_bonus = 0
            missing_skills = []

            # -------------------------------------------------
            # 5️⃣ If JD provided → Extract + Match
            # -------------------------------------------------
            if job.job_description:
                print("[STEP] Extracting structured JD data...")
                jd_data = extract_jd_structured(job.job_description)
                job.extracted_jd_json = jd_data

                required_skills = jd_data.get("required_skills", [])
                optional_skills = jd_data.get("optional_skills", [])
                min_experience = jd_data.get("min_experience_years", 1)

                print("[STEP] Computing skill matching...")
                matched, missing, match_percentage = compute_skill_matching(
                    resume_data.get("skills", []),
                    required_skills
                )

                missing_skills = missing
                job.missing_skills = missing_skills
                job.match_percentage = match_percentage

                # Experience scoring
                resume_experience = resume_data.get("total_experience_years", 0)
                experience_score = min(
                    100,
                    (resume_experience / max(min_experience, 1)) * 100
                )

                # Optional skill bonus
                if optional_skills:
                    matched_optional, _, optional_percentage = compute_skill_matching(
                        resume_data.get("skills", []),
                        optional_skills
                    )
                    optional_bonus = optional_percentage

            else:
                print("[STEP] No JD provided → Using generic scoring.")
                match_percentage = 60
                experience_score = 60
                job.match_percentage = None

            # -------------------------------------------------
            # 6️⃣ Qualitative LLM Analysis
            # -------------------------------------------------
            print("[STEP] Generating qualitative analysis...")
            qualitative = generate_qualitative_analysis(
                resume_text,
                job.job_description
            )

            job.strengths = qualitative.get("strengths")
            job.weaknesses = qualitative.get("weaknesses")
            job.analysis_summary = qualitative.get("summary")

            # -------------------------------------------------
            # 7️⃣ Final Deterministic Score
            # -------------------------------------------------
            print("[STEP] Computing final score...")
            final_score = compute_final_score(
                match_percentage,
                experience_score,
                project_score,
                optional_bonus
            )

            job.overall_score = round(final_score, 2)

            # -------------------------------------------------
            # 8️⃣ Mark Completed
            # -------------------------------------------------
            job.status = "completed"
            db.commit()

            print(f"[TASK COMPLETED] Job {job_id} successfully processed.")

        except Exception as e:
            print(f"[TASK ERROR] Job {job_id} failed.")
            print("Error:", str(e))
            print(traceback.format_exc())

            job.status = "failed"
            db.commit()
