# prd_evaluator.py
from __future__ import annotations

import json
from typing import Dict, Any

from openai import OpenAI

# Initialize OpenAI client (expects OPENAI_API_KEY in environment variables)
client = OpenAI()

MODEL = "gpt-4.1-mini"


def _build_system_prompt() -> str:
    """System prompt instructing the model to behave like a senior product reviewer."""
    return """
You are a senior Product Manager and Product Quality Reviewer.

Your job is to evaluate the quality of Product Requirements Documents (PRDs).

Evaluation principles:
- Be strict but fair.
- Focus on clarity, completeness, measurability, and business value.
- Give short, actionable feedback.
- Do not hallucinate missing information — if something is missing, mention it.

You must return valid JSON only.
"""


def _build_user_prompt(prd: Dict[str, Any], original_notes: str | None) -> str:
    """User prompt containing the generated PRD and optional original notes."""
    notes_section = f"\nORIGINAL NOTES:\n{original_notes}\n" if original_notes else ""

    return f"""
Evaluate the following PRD.

Return evaluation scores and improvement suggestions.

PRD JSON:
{json.dumps(prd, ensure_ascii=False, indent=2)}

{notes_section}
"""


def _get_eval_schema() -> Dict[str, Any]:
    """Defines the expected evaluation JSON structure."""
    return {
        "type": "object",
        "properties": {
            "clarity_score": {
                "type": "number",
                "description": "How clear and understandable the PRD is (0-10)"
            },
            "completeness_score": {
                "type": "number",
                "description": "How complete the PRD is (0-10)"
            },
            "measurability_score": {
                "type": "number",
                "description": "How measurable the goals are (0-10)"
            },
            "business_value_score": {
                "type": "number",
                "description": "How strong the business value is (0-10)"
            },
            "overall_score": {
                "type": "number",
                "description": "Overall quality score (0-10)"
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"}
            },
            "improvements": {
                "type": "array",
                "items": {"type": "string"}
            },
            "summary": {
                "type": "string"
            }
        },
        "required": [
            "clarity_score",
            "completeness_score",
            "measurability_score",
            "business_value_score",
            "overall_score",
            "strengths",
            "improvements",
            "summary"
        ]
    }


def evaluate_prd_quality(
    prd: Dict[str, Any],
    original_notes: str | None = None
) -> Dict[str, Any]:
    """
    Main evaluation function.
    Takes PRD JSON and returns evaluation scores + feedback.
    """

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(prd, original_notes)
    schema = _get_eval_schema()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "prd_evaluation_schema",
                "schema": schema
            }
        }
    )

    content = response.choices[0].message.content

    if isinstance(content, str):
        result = json.loads(content)
    else:
        result = content

    return result
