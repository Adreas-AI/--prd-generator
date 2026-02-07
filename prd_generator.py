# prd_generator.py
from __future__ import annotations

import json
from typing import Dict, Any

from openai import OpenAI

# Initialize OpenAI client (expects OPENAI_API_KEY in environment variables)
client = OpenAI()

MODEL = "gpt-4.1-mini"


def _build_system_prompt() -> str:
    """System prompt that instructs the model to behave like a senior Product Manager."""
    return """
You are a senior Product Manager.

Your job is to convert messy business notes into a structured Product Requirements Document (PRD).

Rules:
- Be realistic and business-focused.
- Do NOT invent features that are not implied by the notes.
- Keep outputs concise but complete.
- If information is missing, add it to "open_questions".
- Goals must be measurable when possible.
- Output MUST be valid JSON matching the schema exactly.
"""


def _build_user_prompt(notes: str) -> str:
    """User prompt containing the raw meeting notes."""
    return f"""
Convert the following business notes into a structured PRD.

NOTES:
{notes}
"""


def _get_prd_json_schema() -> Dict[str, Any]:
    """Defines the expected PRD JSON structure."""
    return {
        "type": "object",
        "properties": {
            "problem": {"type": "string"},
            "users": {"type": "array", "items": {"type": "string"}},
            "goals": {"type": "array", "items": {"type": "string"}},
            "scope": {"type": "array", "items": {"type": "string"}},
            "non_scope": {"type": "array", "items": {"type": "string"}},
            "user_stories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "as_a": {"type": "string"},
                        "i_want": {"type": "string"},
                        "so_that": {"type": "string"}
                    },
                    "required": ["as_a", "i_want", "so_that"]
                }
            },
            "risks": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}}
        },
        "required": [
            "problem",
            "users",
            "goals",
            "scope",
            "non_scope",
            "user_stories",
            "risks",
            "open_questions"
        ]
    }


def generate_prd_from_notes(notes: str) -> Dict[str, Any]:
    """
    Main function used by Streamlit app.
    Takes raw notes and returns structured PRD JSON.
    """

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(notes)
    schema = _get_prd_json_schema()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "prd_schema",
                "schema": schema
            }
        }
    )

    content = response.choices[0].message.content

    if isinstance(content, str):
        prd = json.loads(content)
    else:
        prd = content

    return prd
