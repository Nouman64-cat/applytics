from pydantic import BaseModel, Field


class KeywordAnalysisOutput(BaseModel):
    extracted_keywords: list[str] = Field(
        description="Strong keywords/skills already present in the profile that are relevant to the target role"
    )
    missing_keywords: list[str] = Field(
        description="Important keywords/skills the target role calls for that are missing or weakly represented"
    )
    ats_score: int = Field(
        ge=0, le=100, description="0-100: how well this profile would match an ATS keyword scan for the target role"
    )
    recruiter_attention_score: int = Field(
        ge=0, le=100, description="0-100: how likely this profile is to catch a human recruiter's attention"
    )
    rationale: str = Field(description="1-3 sentence explanation of the scores")


class LocationAnalysisOutput(BaseModel):
    location_penalty_score: int = Field(
        ge=0,
        le=100,
        description=(
            "0-100: how much the candidate's current location likely hurts their odds for "
            "100%-remote US-based roles (0 = no penalty, 100 = severe penalty)"
        ),
    )
    recommendation: str = Field(
        description="Concrete recommendation for the BD on how to mitigate any location-related penalty"
    )


class ProfileScore(BaseModel):
    profile_id: str = Field(description="The exact Profile ID as given in the input, unchanged")
    strengths: list[str]
    weaknesses: list[str]
    score: int = Field(ge=0, le=100)


class ComparisonOutput(BaseModel):
    winner_profile_id: str | None = Field(
        default=None,
        description="The profile_id of the strongest profile, or null for a genuine tie / insufficient data",
    )
    bottlenecks: list[str] = Field(description="Specific, actionable bottlenecks found across the compared profiles")
    summary: str = Field(description="2-4 sentence overall summary of the comparison and recommendation")


class KeywordSuggestionOutput(BaseModel):
    keywords: list[str] = Field(
        description=(
            "6-10 job-search query strings a Business Developer could paste into a job board's search box, "
            "ranked roughly broad-to-specific, covering common title variants/synonyms and seniority levels"
        )
    )


class JobMatchScore(BaseModel):
    job_id: str = Field(description="The exact job id as given in the input, unchanged")
    score: int = Field(ge=0, le=100, description="0-100 suitability score for this candidate's resume")
    rationale: str = Field(description="1-2 sentence explanation referencing specific resume content")


class JobMatchOutput(BaseModel):
    matches: list[JobMatchScore] = Field(
        description=(
            "Jobs ranked best-fit first. Omit jobs that are clearly not a good fit entirely rather than "
            "including them with a low score."
        )
    )


class ResumeExtraction(BaseModel):
    full_name: str | None = Field(default=None, description="The candidate's full name, or null if not found")
    email: str | None = Field(default=None, description="The candidate's email address, or null if not found")
    current_city: str | None = Field(default=None, description="The candidate's current city, or null if not found")
    current_state: str | None = Field(
        default=None, description="The candidate's current state/region, or null if not found"
    )
    current_country: str | None = Field(
        default=None, description="The candidate's current country, or null if not found"
    )
    raw_text: str = Field(description="The complete plain-text content of the resume")
