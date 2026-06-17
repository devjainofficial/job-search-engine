"""Seed registry of public ATS boards (verified to return jobs).

These slugs were probed live against each ATS endpoint. Discovery at scale
(Common Crawl, open slug registries) is a later task; for now this is a curated
starter set. Greenhouse jobs carry company_name; Lever/Ashby do not, so those
list (slug, display_name) pairs.
"""

# boards-api.greenhouse.io/v1/boards/{token}/jobs  (company_name is in each job)
GREENHOUSE = [
    "stripe", "airbnb", "gitlab", "dropbox", "coinbase", "databricks", "figma",
    "discord", "instacart", "asana", "brex", "robinhood", "cloudflare",
    "datadog", "reddit", "postman",
]

# api.lever.co/v0/postings/{slug}?mode=json
LEVER = [
    ("spotify", "Spotify"),
    ("mistral", "Mistral AI"),
    ("palantir", "Palantir"),
]

# api.ashbyhq.com/posting-api/job-board/{slug}
ASHBY = [
    ("openai", "OpenAI"),
    ("ramp", "Ramp"),
    ("linear", "Linear"),
    ("notion", "Notion"),
    ("cohere", "Cohere"),
    ("replit", "Replit"),
    ("posthog", "PostHog"),
    ("runway", "Runway"),
    ("browserbase", "Browserbase"),
]
