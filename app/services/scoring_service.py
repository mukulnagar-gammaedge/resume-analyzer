def compute_final_score(
    skill_match,
    experience_score,
    project_score,
    optional_bonus
):
    return (
        skill_match * 0.5 +
        experience_score * 0.2 +
        project_score * 0.2 +
        optional_bonus * 0.1
    )
