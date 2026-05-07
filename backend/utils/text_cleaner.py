"""
Text preprocessing and title normalization for deduplication.
Applied at upsert time so the DB always stores clean data.
"""

import html
import re

_TAG_RE        = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'[ \t\r\n]+')
_DEDUP_RE      = re.compile(r'[^a-z0-9\s]')
_MULTI_SPC_RE  = re.compile(r'\s{2,}')

# Common LaTeX-style tokens that add noise without meaning
_LATEX_RE = re.compile(r'\$[^$]*\$|\\\w+\{[^}]*\}|\\\w+')


def clean_text(text: str) -> str:
    """Decode HTML entities, strip tags, collapse whitespace."""
    if not text:
        return ""
    text = html.unescape(text)          # &amp; &lt; &#x27; → plain chars
    text = _LATEX_RE.sub(' ', text)     # $E=mc^2$ → ' '
    text = _TAG_RE.sub(' ', text)       # <sub>2</sub> → ' '
    text = _WHITESPACE_RE.sub(' ', text)
    return text.strip()


def clean_title(text: str) -> str:
    return clean_text(text)


def clean_abstract(text: str) -> str:
    return clean_text(text)


def is_valid_abstract(text: str, min_chars: int = 80) -> bool:
    """Return False when abstract is absent or clearly a placeholder."""
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    # Reject pure-noise strings (all punctuation / numbers only)
    if re.fullmatch(r'[\W\d\s]+', stripped):
        return False
    return True


def normalize_title(title: str) -> str:
    """
    Normalize a title for cross-source duplicate detection.
    Lowercases, removes non-alphanumeric chars, collapses spaces.
    Two titles that map to the same string are considered the same paper.
    """
    if not title:
        return ""
    t = title.lower()
    t = _DEDUP_RE.sub('', t)
    t = _MULTI_SPC_RE.sub(' ', t)
    return t.strip()
