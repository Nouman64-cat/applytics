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
        return "No specific target role provided — evaluate for a general 100% remote US job search."
    keywords = ", ".join(target_role.must_have_keywords) or "none specified"
    return f"Target role: {target_role.title} (seniority: {target_role.seniority or 'unspecified'})\nMust-have keywords: {keywords}"


def _profile_block(profile: Profile) -> str:
    return (
        f"Profile ID: {profile.id}\n"
        f"Type: {profile.type.value}\n"
        f"Variant label: {profile.variant_label}\n"
        f"Text:\n{profile.raw_text or '(no text available)'}"
    )


def build_comparison_graph(session: AsyncSession):
    async def score_profiles(state: ComparisonState) -> dict:
        role_context = _role_context(state["target_role"])
        scores: list[ProfileScore] = []
        for profile in state["profiles"]:
            prompt = (
                "You are evaluating one candidate profile in isolation, as part of an A/B comparison "
                "of multiple profile variants targeting the same role. Rate its strengths and weaknesses "
                "for a 100% remote US job search.\n\n"
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
            "Given these independently-scored candidate profile variants for the same target role, "
            "synthesize a comparison: name the strongest profile by its exact profile_id (or note a tie / "
            "insufficient data with null), list concrete cross-cutting bottlenecks, and summarize your "
            "recommendation.\n\n"
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
