from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_structured
from agents.schemas import ComparisonOutput, ProfileScore
from db.models import Profile, TargetRole


class ComparisonState(TypedDict):
    profiles: list[Profile]
    target_role: TargetRole | None
    profile_scores: list[ProfileScore]
    result: ComparisonOutput | None


def _role_context(target_role: TargetRole | None) -> str:
    if target_role is None:
        return (
            "No specific target role provided — evaluate for a general 100% remote job search "
            "targeting USA-based companies."
        )
    keywords = ", ".join(target_role.must_have_keywords) or "none specified"
    return f"Target role: {target_role.title} (seniority: {target_role.seniority or 'unspecified'})\nMust-have keywords: {keywords}"


def _profile_block(profile: Profile) -> str:
    return (
        f"Profile ID: {profile.id}\n"
        f"Type: {profile.type.value}\n"
        f"Variant label: {profile.variant_label}\n"
        f"Resume text:\n{profile.raw_text or '(no text available)'}"
    )


def build_comparison_graph(session: AsyncSession):
    async def score_profiles(state: ComparisonState) -> dict:
        role_context = _role_context(state["target_role"])
        scores: list[ProfileScore] = []
        for profile in state["profiles"]:
            prompt = (
                "You are evaluating one candidate's resume in isolation, as part of an A/B comparison "
                "of multiple resume variants targeting the same role at USA-based companies. Every "
                "hiring manager, recruiter, and ATS you are evaluating against is American — assume US "
                "hiring conventions and resume-format expectations throughout. Rate this resume's "
                "strengths and weaknesses for a 100% remote job search targeting the USA market.\n\n"
                f"{role_context}\n\n{_profile_block(profile)}\n\n"
                f'Set profile_id in your response to exactly: "{profile.id}"'
            )
            score = await run_structured(
                session,
                agent_type="comparison_score",
                related_entity_type="profile",
                related_entity_id=profile.id,
                prompt=prompt,
                output_model=ProfileScore,
            )
            scores.append(score)
        return {"profile_scores": scores}

    async def synthesize(state: ComparisonState) -> dict:
        scores_text = "\n\n".join(
            f"Profile {s.profile_id} (score {s.score}/100)\nStrengths: {s.strengths}\nWeaknesses: {s.weaknesses}"
            for s in state["profile_scores"]
        )
        prompt = (
            "Given these independently-scored resume variants for the same candidate and target role — "
            "all evaluated against USA-based companies' hiring standards and ATS systems — synthesize a "
            "comparison: name the strongest resume by its exact profile_id (or note a tie / insufficient "
            "data with null), list concrete cross-cutting bottlenecks explaining specifically why the "
            "weaker resume(s) would likely fail with American employers (e.g. ATS-unfriendly formatting, "
            "missing US-expected keywords or sections, unclear work authorization, non-US resume "
            "conventions), and summarize your recommendation.\n\n"
            f"{scores_text}"
        )
        result = await run_structured(
            session,
            agent_type="comparison_synthesis",
            related_entity_type="client",
            related_entity_id=state["profiles"][0].client_id,
            prompt=prompt,
            output_model=ComparisonOutput,
        )
        return {"result": result}

    graph = StateGraph(ComparisonState)
    graph.add_node("score_profiles", score_profiles)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("score_profiles")
    graph.add_edge("score_profiles", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
