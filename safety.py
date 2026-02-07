# safety.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class SafetyResult:
    ok: bool
    reason: str = ""
    flags: Optional[List[str]] = None


# Common prompt-injection/jailbreak patterns for business-input tools
_INJECTION_PATTERNS = [
    r"\bignore (all|any|the) (previous|prior) instructions\b",
    r"\bdisregard (all|any|the) (previous|prior) instructions\b",
    r"\byou are now\b",
    r"\bact as\b.*\b(system|developer)\b",
    r"\b(system|developer) prompt\b",
    r"\breveal\b.*\b(system prompt|hidden prompt|instructions)\b",
    r"\bprint\b.*\b(system prompt|developer message|secret)\b",
    r"\bapi[_ -]?key\b",
    r"\bpassword\b",
    r"\btoken\b",
    r"\bexfiltrate\b",
    r"\bdata leak\b",
    r"\bdo not follow\b",
    r"\boverride\b.*\brules\b",
]


# Very basic “harmful intent” patterns (keep light; moderation handles the rest)
_HARMFUL_HINTS = [
    r"\bkill\b",
    r"\bmurder\b",
    r"\bweapon\b",
    r"\bbomb\b",
    r"\bsuicide\b",
    r"\bterror\b",
]


def heuristic_safety_check(text: str) -> SafetyResult:
    """
    Lightweight local checks:
    - Block obvious prompt-injection attempts
    - Block obvious harmful intent (very basic)
    """
    flags: List[str] = []
    t = (text or "").strip()
    if not t:
        return SafetyResult(ok=False, reason="Input is empty.", flags=["empty_input"])

    lowered = t.lower()

    # Injection checks
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, lowered, flags=re.IGNORECASE):
            flags.append("prompt_injection_pattern")
            break

    # Harmful hints (very basic)
    for pat in _HARMFUL_HINTS:
        if re.search(pat, lowered, flags=re.IGNORECASE):
            flags.append("harmful_hint")
            break

    if "prompt_injection_pattern" in flags:
        return SafetyResult(
            ok=False,
            reason=(
                "Potential prompt-injection detected. "
                "Please remove instructions like 'ignore previous instructions', references to system prompts, or requests for secrets."
            ),
            flags=flags,
        )

    if "harmful_hint" in flags:
        return SafetyResult(
            ok=False,
            reason="Potentially harmful content detected. Please provide business/product notes only.",
            flags=flags,
        )

    return SafetyResult(ok=True, flags=flags)


def openai_moderation_check(text: str) -> SafetyResult:
    """
    Optional OpenAI moderation check.
    If moderation is unavailable (network/model), it fails open with ok=True.
    """
    try:
        from openai import OpenAI

        client = OpenAI()

        # Model name may vary by account; keep this as a sensible default.
        resp = client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )

        # Typical response: results[0].flagged boolean
        flagged = bool(resp.results[0].flagged)
        if flagged:
            return SafetyResult(
                ok=False,
                reason="Input was flagged by moderation. Please provide business/product notes only.",
                flags=["moderation_flagged"],
            )
        return SafetyResult(ok=True, flags=["moderation_ok"])

    except Exception:
        # Fail open: do not block if moderation is unavailable
        return SafetyResult(ok=True, flags=["moderation_unavailable"])


def safety_check(text: str, use_moderation: bool = True) -> SafetyResult:
    """
    Combined safety check:
    1) Heuristics (prompt injection + basic harmful intent)
    2) Optional moderation (fail-open)
    """
    h = heuristic_safety_check(text)
    if not h.ok:
        return h

    if use_moderation:
        m = openai_moderation_check(text)
        if not m.ok:
            return m

    return SafetyResult(ok=True, flags=(h.flags or []))
