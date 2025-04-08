# ATS Score Calculation Methodology
*Documentation for ATS Compatibility Scoring in CV Optimization*

## Overview
This document outlines the methodology used to calculate the ATS (Applicant Tracking System) compatibility score for a resume against a job description. The goal is to provide a dynamic, effective, and simple scoring system that aligns with how ATS systems evaluate resumes, enabling targeted optimization to a user-defined score between 75% and 100%.

## Background
ATS systems are widely used by companies to filter resumes based on textual content, focusing on:
- **Keywords**: Specific words or phrases from the job description.
- **Skills**: Technical and soft skills required for the role.
- **Experience**: Years of relevant experience or job titles.

Tools like Jobscan and Zety suggest a target ATS score of 75-80% for a resume to pass initial screening. Our methodology builds on these principles, ensuring simplicity and portability for use in a Dockerized environment.

## Methodology

### Step 1: Data Extraction
A Language Model (LLM) is used to extract structured data from both the job description and the resume:
- **Job Description**:
  - **Skills**: List of required skills (e.g., "Python", "Machine Learning").
  - **Experience**: Minimum years required (e.g., "3" from "3+ years").
  - **Keywords**: Top 10 most relevant keywords/phrases (e.g., "data analysis", "cloud computing").
- **Resume**:
  - **Skills**: List of candidate skills.
  - **Experience**: Total years of experience.
  - **Full Text**: For keyword matching.

**Prompt Example (Job Description)**:
Extract:

    A list of required skills.
    The minimum years of experience required (as a number).
    The 10 most important keywords or phrases. Return as JSON: {"skills": [], "experience": "", "keywords": []}


### Step 2: ATS Score Calculation
The score is a weighted average of three components, reflecting ATS priorities:
- **Skills (40%)**:
  - Formula: \( \text{skills_score} = \left( \frac{\text{number of required skills in resume}}{\text{total required skills}} \right) \times 100 \)
  - If no skills are required, score is 100%.
  - Example: Job requires Python, SQL, ML (3); resume has Python, SQL (2). Score = \( (2/3) \times 100 = 66.67\% \).

- **Experience (30%)**:
  - Formula:
    \[
    \text{experience_score} = \begin{cases} 
    100 & \text{if resume experience} \geq \text{required experience} \\
    \left( \frac{\text{resume experience}}{\text{required experience}} \right) \times 100 & \text{otherwise}
    \end{cases}
    \]
  - If no experience is specified, score is 100%.
  - Example: Job requires 3 years, resume has 2. Score = \( (2/3) \times 100 = 66.67\% \).

- **Keywords (30%)**:
  - Formula: \( \text{keywords_score} = \left( \frac{\text{number of job keywords in resume text}}{\text{total job keywords}} \right) \times 100 \)
  - Case-insensitive full-text search.
  - Example: Job keywords are "data analysis", "ML", "cloud" (3); resume has "data analysis", "cloud" (2). Score = \( (2/3) \times 100 = 66.67\% \).

- **Overall Score**:
  - Formula: \( \text{overall_score} = 0.4 \times \text{skills_score} + 0.3 \times \text{experience_score} + 0.3 \times \text{keywords_score} \)
  - Capped at 100%.
  - Example: All sub-scores at 66.67%. Total = \( 0.4 \times 66.67 + 0.3 \times 66.67 + 0.3 \times 66.67 = 66.67\% \).

### Step 3: Dynamic Adaptation
The system adapts the resume based on the gap between the initial score and the user-defined target score (75-100%):
- **Gap Calculation**: \( \text{gap} = \text{target_score} - \text{initial_score} \)
- **Dynamic Prompts**:
  - **Gap ≤ 10%**: Emphasize existing matches, minor tweaks.
  - **Gap 11-30%**: Add missing skills/keywords naturally, adjust experience.
  - **Gap > 30%**: Rewrite sections to maximize compatibility.
- **Details Provided**: Missing skills, keywords, and experience gap are included in the prompt.

### Implementation Notes
- **Weights**: 40% skills, 30% experience, 30% keywords are based on typical ATS priorities for technical roles. Adjustable for other job types.
- **Simplicity**: Avoids complex embeddings or external tools for portability.
- **Validation**: Final score is recalculated post-optimization to confirm the target is met.

## Example
- **Job**: "Developer, 3+ years, Python, Django, Agile."
- **Resume**: "Developer, 2 years, Python, Flask."
- **Initial Score**: ~60% (skills: 1/3, exp: 2/3, keywords: 2/3).
- **Target**: 85%.
- **Gap**: 25% (moderate adaptation).
- **Optimized Resume**: Adds "Django" and "Agile" naturally, adjusts experience.
- **Final Score**: ~85%.

## References
- [Jobscan Resume Score](https://www.jobscan.co/resume-score)
- [Workable: How ATS Reads Resumes](https://resources.workable.com/stories-and-insights/how-ATS-reads-resumes)
- [TealHQ Resume Parsing](https://www.tealhq.com/post/resume-parsing)    