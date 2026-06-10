from pydantic import BaseModel, Field
from typing import List


class UserProfileSummary(BaseModel):
    """Pydantic schema constraining Gemini's JSON output to a valid user persona profile."""

    interests: List[str] = Field(
        description="Key topics the user is interested in, inferred from 'search' or 'view' actions."
    )
    dislikes: List[str] = Field(
        description="Topics the user has dismissed or avoided, inferred from 'dismiss' actions."
    )
    persona: str = Field(
        description=(
            "A cohesive 1-2 sentence summary paragraph characterizing the user's role, "
            "behavioral trends, and inferred goals based on their recent interactions."
        )
    )
    communication_style: str = Field(
        description=(
            "The preferred communication style. Must be exactly one of: "
            "'casual', 'technical', 'analytical', 'concise'."
        )
    )
    technical_depth: str = Field(
        description=(
            "The estimated technical detail level the user prefers. Must be exactly one of: "
            "'beginner', 'intermediate', 'advanced'."
        )
    )


USER_PROFILE_SYNTHESIS_PROMPT = """\
You are an expert user behavior analyst embedded in a hyper-personalization AI engine.
Your job is to analyze a raw list of user interaction logs and synthesize them into a \
structured JSON persona profile.

## Your Rules
1. Infer 'interests' from topics the user has searched or viewed.
2. Infer 'dislikes' from topics the user has dismissed or repeatedly ignored.
3. Write 'persona' as a short, insightful 1-2 sentence narrative describing who this user \
   likely is and what they care about. Be specific — avoid generic filler.
4. Infer 'communication_style' from the nature and frequency of their actions:
   - 'technical'   → heavy search activity on complex/specialized topics
   - 'analytical'  → balanced mix of searching and reading, diverse topics
   - 'casual'      → mostly view actions, lighter topics
   - 'concise'     → few events, fast dismiss patterns
5. Infer 'technical_depth' based on topic sophistication:
   - 'advanced'     → topics like quantum computing, distributed systems, ML architectures
   - 'intermediate' → topics like machine learning, cloud computing, algorithms
   - 'beginner'     → topics like general tech news, introductory concepts

## Interaction Logs to Analyze
{events_json}

## Output
You MUST return a JSON object that strictly conforms to the provided schema.
Do NOT add any explanatory text, markdown code fences, or extra fields.
"""
