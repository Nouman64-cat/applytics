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
