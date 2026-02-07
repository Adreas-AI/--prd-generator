# app.py
from __future__ import annotations

import json
import streamlit as st

from prd_generator import generate_prd_from_notes
from prd_evaluator import evaluate_prd_quality
from safety import safety_check

APP_TITLE = "AI PRD Generator (Notes → PRD + Evaluation)"


def render_prd_markdown(prd: dict) -> str:
    """Convert PRD JSON into formatted markdown for display."""
    def bullet_list(items):
        if not items:
            return "_(none)_"
        return "\n".join([f"- {x}" for x in items])

    user_stories = prd.get("user_stories") or []
    if isinstance(user_stories, list) and user_stories and isinstance(user_stories[0], dict):
        stories_md = "\n".join(
            [
                f"- **As a** {s.get('as_a','')} **I want** {s.get('i_want','')} **so that** {s.get('so_that','')}"
                for s in user_stories
            ]
        ) or "_(none)_"
    else:
        stories_md = bullet_list(user_stories)

    md = f"""
## Problem
{prd.get("problem","").strip() or "_(empty)_"}

## Users / Personas
{bullet_list(prd.get("users") or [])}

## Goals (measurable)
{bullet_list(prd.get("goals") or [])}

## Scope (What we will build)
{bullet_list(prd.get("scope") or [])}

## Non-Scope (What we will NOT build)
{bullet_list(prd.get("non_scope") or [])}

## User Stories
{stories_md}

## Risks
{bullet_list(prd.get("risks") or [])}

## Open Questions
{bullet_list(prd.get("open_questions") or [])}
"""
    return md.strip()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Paste messy business notes → get a structured PRD + quality evaluation.")

    # Sidebar settings
    with st.sidebar:
        st.subheader("Settings")
        run_eval = st.checkbox("Run PRD quality evaluation (scores)", value=True)
        use_moderation = st.checkbox("Use moderation (recommended)", value=True)
        st.divider()
        st.write("Tip: Start with 6–10 bullet notes.")

    tab1, tab2 = st.tabs(["🧾 Generate PRD", "✅ Evaluation / Export"])

    # ---------- TAB 1: GENERATE ----------
    with tab1:
        st.subheader("1) Paste your notes")

        default_notes = """Meeting Notes:
- Customers complain about slow responses
- Support team overloaded with tickets
- Need AI reply suggestions (draft replies)
- Currently using Zendesk
- Want to pilot in Greece first
- Need copy button and PDF export
"""
        notes = st.text_area("Notes / transcript", value=default_notes, height=220)

        col_a, col_b = st.columns([1, 2])
        with col_a:
            generate_btn = st.button("✨ Generate PRD", type="primary", use_container_width=True)
        with col_b:
            st.write("")

        if generate_btn:
            if not notes.strip():
                st.error("Please add notes first.")
                st.stop()

            # Safety gate (prompt-injection + optional moderation)
            safety = safety_check(notes, use_moderation=use_moderation)
            if not safety.ok:
                st.error(safety.reason)
                st.stop()

            with st.spinner("Generating PRD from notes..."):
                prd = generate_prd_from_notes(notes)

            # Store PRD in session state for use in Tab 2
            st.session_state["prd_json"] = prd

            st.success("PRD generated successfully ✅")
            st.markdown(render_prd_markdown(prd))

            with st.expander("View PRD as JSON"):
                st.code(json.dumps(prd, ensure_ascii=False, indent=2), language="json")

            if run_eval:
                with st.spinner("Evaluating PRD quality..."):
                    eval_result = evaluate_prd_quality(prd, original_notes=notes)

                st.session_state["prd_eval"] = eval_result

                st.info("Evaluation summary")
                st.json(eval_result)

    # ---------- TAB 2: EVALUATION / EXPORT ----------
    with tab2:
        st.subheader("2) Evaluation / Export")

        prd = st.session_state.get("prd_json")
        if not prd:
            st.warning("No PRD found. Go to 'Generate PRD' tab first.")
            st.stop()

        st.markdown("### PRD (Formatted)")
        st.markdown(render_prd_markdown(prd))

        eval_result = st.session_state.get("prd_eval")
        st.markdown("### Scores / Feedback")

        if eval_result:
            st.json(eval_result)
        else:
            st.write("_(Evaluation not run yet)_")

        st.markdown("### Export")
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            md_text = render_prd_markdown(prd)
            st.download_button(
                "⬇ Download PRD as Markdown (.md)",
                data=md_text.encode("utf-8"),
                file_name="prd.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with export_col2:
            prd_json_text = json.dumps(prd, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇ Download PRD as JSON (.json)",
                data=prd_json_text.encode("utf-8"),
                file_name="prd.json",
                mime="application/json",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()


