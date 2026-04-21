"""Text cleanup utilities for party names from EPO/KIPRIS."""
import re


def clean_party_name(name: str) -> str:
    """Remove EPO country suffixes [KR] [US] etc. and normalize whitespace."""
    if not name:
        return name
    # Remove [XX] country codes
    cleaned = re.sub(r"\s*\[[A-Z]{2}\]", "", name).strip()
    # Normalize multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def clean_assignee(raw: str) -> str:
    """Clean semicolon-separated list of assignee names."""
    if not raw:
        return raw
    parts = [clean_party_name(p) for p in raw.split(";")]
    return "; ".join(p for p in parts if p)


def clean_inventors(raw: str) -> str:
    """Clean comma-separated list of inventor names."""
    if not raw:
        return raw
    parts = [clean_party_name(p) for p in raw.split(",")]
    return ", ".join(p for p in parts if p)
