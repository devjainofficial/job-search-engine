"""Parse resume text into a structured Profile using Gemini 2.5 Flash-Lite.

Parse-once: this is called from the upload/seed path only, never on a daily run
(that is the single biggest cost control). A resume is ~1-2k tokens, so at
Gemini 2.5 Flash-Lite pricing ($0.10/1M in, $0.40/1M out) a parse costs a
fraction of a cent. Note: the Gemini free tier may NOT be used for EEA/UK end
users (see docs/RESEARCH.md); a paid key is required there.
"""

import json

import litellm

from app.config import get_settings
from app.models import Profile

# LiteLLM reads GEMINI_API_KEY from the environment; we pass it explicitly so the
# worker's pydantic settings remain the single source of truth.
MODEL = "gemini/gemini-2.5-flash-lite"

_SYSTEM = (
    "You extract a structured job-search profile from resume text. "
    "Respond with ONLY a JSON object, no prose, matching exactly these keys:\n"
    '{"role_titles": [string], "skills": [string], '
    '"years_experience": integer or null, "location": string or null, '
    '"remote_pref": one of "remote"|"onsite"|"hybrid"|"any" or null}\n'
    "role_titles: 2-5 concise target job titles the candidate fits. "
    "skills: key technical and domain skills. "
    "location: city/region if stated. Infer remote_pref only if clearly implied, "
    "else null."
)


def parse_resume_text(text: str) -> Profile:
    settings = get_settings()
    response = litellm.completion(
        model=MODEL,
        api_key=settings.gemini_api_key or None,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text[:20000]},  # guard against huge inputs
        ],
        response_format={"type": "json_object"},
        temperature=0,
        # Gemini returns transient 429/503 under load; back off and retry rather
        # than failing a parse outright (parsing is one-shot per resume).
        num_retries=3,
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    return Profile.model_validate(data)
