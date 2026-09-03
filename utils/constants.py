"""
Project Nexus

Constants
"""

ROLE_CREATOR = "creator"

ROLE_SPECIAL = "special"

ROLE_ADMIN = "admin"

ROLE_USER = "user"


#: How aggressively Nexus looks things up before answering.
SEARCH_MODES = ("auto", "always", "never")

#: How evidence is credited in a reply.
CITATION_MODES = ("auto", "footer", "inline", "off")

#: How often the answer must be re-grounded before it may be stated as fact.
ACCURACY_PRESETS = {
    "strict": {
        "search_mode": "always",
        "min_sources_for_grounding": 2,
        "citation_mode": "footer",
    },
    "balanced": {
        "search_mode": "auto",
        "min_sources_for_grounding": 1,
        "citation_mode": "auto",
    },
    "fast": {
        "search_mode": "auto",
        "min_sources_for_grounding": 1,
        "citation_mode": "off",
    },
    "offline": {
        "search_mode": "never",
        "min_sources_for_grounding": 1,
        "citation_mode": "off",
    },
}
