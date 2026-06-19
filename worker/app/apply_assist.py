"""AI apply-assist: generate a tailored cover letter + draft answers to common
screening questions from the user's profile and a specific job, via Gemini.

One LLM call per request (a few tenths of a cent). This is the legal, safe
alternative to auto-apply: it drafts materials the user reviews and submits.
"""

import json

import litellm

from app.config import get_settings
from app.parsing.resume_parser import MODEL  # reuse the Gemini 2.5 Flash-Lite model id

_SYSTEM = (
    "You help a job seeker apply faster. Given their profile and a job, write a "
    "concise, specific, non-generic cover letter (about 150 words, first person, "
    "no placeholders or [brackets]) and short draft answers to 3 common screening "
    "questions. Respond with ONLY JSON: "
    '{"cover_letter": string, "answers": [{"q": string, "a": string}]}'
)


def generate_application(profile: dict, job: dict) -> dict:
    settings = get_settings()
    prompt = (
        f"CANDIDATE PROFILE:\n"
        f"Roles: {', '.join(profile.get('role_titles') or [])}\n"
        f"Skills: {', '.join(profile.get('skills') or [])}\n"
        f"Years of experience: {profile.get('years_experience')}\n"
        f"Location: {profile.get('location')}\n\n"
        f"JOB:\n"
        f"Title: {job.get('title')}\n"
        f"Company: {job.get('company')}\n"
        f"Location: {job.get('location')}\n"
        f"Description: {(job.get('description') or '')[:4000]}\n"
    )
    response = litellm.completion(
        model=MODEL,
        api_key=settings.gemini_api_key or None,
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
        num_retries=2,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return {
        "cover_letter": data.get("cover_letter", ""),
        "answers": data.get("answers", []),
    }
