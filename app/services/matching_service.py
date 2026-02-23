def compute_skill_matching(resume_skills, required_skills):
    resume_set = set([s.lower() for s in resume_skills])
    required_set = set([s.lower() for s in required_skills])

    matched = resume_set & required_set
    missing = required_set - resume_set

    match_percentage = (
        len(matched) / len(required_set) * 100 if required_set else 0
    )

    return list(matched), list(missing), match_percentage
