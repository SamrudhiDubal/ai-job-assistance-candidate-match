"""Optional LLM semantic scoring with Claude (Module 7).

Switched on only when the ANTHROPIC_API_KEY environment variable is set. Claude
reads the job and the resume as an experienced technical recruiter would and
returns a 0-100 fit score and a short summary for the employer. Any problem
(no key, network error, refusal, unexpected reply) returns None, and the local
score is used unchanged, so the portal never depends on an external service.
"""
import json
import logging
import os

log = logging.getLogger("jobmatch.screening")

MODEL = os.environ.get("JOBMATCH_LLM_MODEL", "claude-opus-5-5")
MAX_CHARS = 6000  # long resumes and job posts are cut to keep each call small and cheap

SYSTEM = (
    "You are an experienced technical recruiter. Rate how well the candidate's resume fits the job, "
    "from 0 (no fit) to 100 (excellent fit), judging skills, relevant experience and seniority. "
    "Ignore the candidate's name, gender, age, location and any other personal characteristics. "
    "Write the summary for the hiring manager in at most 40 words."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "Fit from 0 to 100"},
        "summary": {"type": "string", "description": "At most 40 words"},
    },
    "required": ["score", "summary"],
    "additionalProperties": False,
}


def enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def rate(resume_text, job_text):
    """Return {"score": int, "summary": str} or None."""
    if not enabled():
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(timeout=60.0)
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{
                "role": "user",
                "content": f"<job>\n{job_text[:MAX_CHARS]}\n</job>\n\n<resume>\n{resume_text[:MAX_CHARS]}\n</resume>",
            }],
        )
        if response.stop_reason == "refusal":
            return None
        text = next((b.text for b in response.content if b.type == "text"), None)
        data = json.loads(text)
        return {"score": max(0, min(100, int(data["score"]))), "summary": str(data["summary"])[:400]}
    except Exception as exc:
        log.warning("LLM scoring skipped: %s", exc)
        return None
