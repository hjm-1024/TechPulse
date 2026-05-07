"""
Lens.org patent collector — worldwide patent database (US, EP, WO, KR, JP).

Free tier: 10,000 requests/month
Registration: https://www.lens.org → Sign Up → Profile → API Access

Set in .env:
    LENS_API_KEY=<your key>
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

try:
    from backend.config import LENS_API_KEY
except ImportError:
    LENS_API_KEY = ""

logger = get_logger(__name__)

_SEARCH_URL      = "https://api.lens.org/patent/search"
_PAGE_SIZE       = 100
_RATE_LIMIT_SECS = 0.5   # free tier is generous; 0.5s is safe
_MAX_RETRIES     = 4


def _build_payload(keyword: str, days_back: int, offset: int) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": f'"{keyword}"',
                            "fields": ["title", "abstract"],
                            "default_operator": "AND",
                        }
                    },
                    {"range": {"date_published": {"gte": since}}},
                ]
            }
        },
        "size": _PAGE_SIZE,
        "from": offset,
        "sort": [{"date_published": "desc"}],
        "include": [
            "lens_id",
            "title",
            "abstract",
            "inventors",
            "applicants",
            "date_published",
            "date_published",
            "filing_date",
            "doc_number",
            "jurisdiction",
            "classifications_ipcr",
        ],
    }


def _parse_hit(hit: dict, keyword: str, domain_tag_map=None) -> dict | None:
    title = (hit.get("title") or "").strip()
    if not title:
        return None

    abstract = (hit.get("abstract") or "").replace("\n", " ").strip()

    doc_number   = (hit.get("doc_number") or hit.get("lens_id") or "").strip()
    jurisdiction = (hit.get("jurisdiction") or "WO").strip()
    patent_number = f"{jurisdiction}{doc_number}" if doc_number else ""
    if not patent_number:
        return None

    pub_date  = (hit.get("date_published") or "")[:10]
    file_date = (hit.get("filing_date") or "")[:10]

    inv_raw = hit.get("inventors") or []
    inventors = ", ".join(
        (i.get("extracted_name") or {}).get("value", "")
        or f"{i.get('first_name','')} {i.get('last_name','')}".strip()
        for i in inv_raw
        if isinstance(i, dict)
    )

    app_raw = hit.get("applicants") or []
    assignee = "; ".join(
        (a.get("extracted_name") or {}).get("value", "")
        or (a.get("name") or "")
        for a in app_raw
        if isinstance(a, dict)
    )

    cls_raw = (hit.get("classifications_ipcr") or {}).get("classifications") or []
    ipc_codes = ", ".join(
        (c.get("symbol") or "").strip()
        for c in cls_raw[:5]
        if isinstance(c, dict)
    )

    return {
        "patent_number": patent_number,
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": file_date,
        "publication_date": pub_date,
        "ipc_codes": ipc_codes,
        "source": "lens",
        "country": jurisdiction,
        "domain_tag": (domain_tag_map or DOMAIN_TAG_MAP).get(keyword, "other"),
    }


def _fetch_page(payload: dict, session: requests.Session) -> tuple[list[dict], int]:
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = session.post(_SEARCH_URL, json=payload, timeout=30)
        except requests.RequestException as exc:
            logger.warning("Lens request error (attempt %d): %s", attempt + 1, exc)
            time.sleep(delay); delay *= 2
            continue

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("Lens rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait); delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("Lens server error %d (attempt %d); sleeping %.0fs",
                           resp.status_code, attempt + 1, delay)
            time.sleep(delay); delay *= 2
            continue

        if not resp.ok:
            logger.error("Lens HTTP %d: %s", resp.status_code, resp.text[:300])
            return [], 0

        data = resp.json()
        total = data.get("total", 0)
        hits  = data.get("data") or data.get("hits") or []
        return hits, int(total)

    raise requests.RequestException(f"Lens: gave up after {_MAX_RETRIES} retries")


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
    domain_tag_map: dict | None = None,
) -> Generator[dict, None, None]:
    """Yield worldwide patent dicts. Skips if LENS_API_KEY not set."""
    if not LENS_API_KEY:
        logger.warning(
            "LENS_API_KEY not set — skipping Lens collection. "
            "Get a free key at https://www.lens.org (Profile → API Access)."
        )
        return

    if keywords is None:
        keywords = KEYWORDS

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {LENS_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "TechPulse/1.0 (research dashboard)",
    })

    for keyword in keywords:
        logger.info("Lens | keyword=%r | days_back=%d", keyword, days_back)

        offset  = 0
        fetched = 0

        while fetched < max_per_keyword:
            payload = _build_payload(keyword, days_back, offset)
            try:
                hits, total = _fetch_page(payload, session)
            except requests.RequestException as exc:
                logger.error("Lens fetch failed (keyword=%r, offset=%d): %s", keyword, offset, exc)
                break

            if not hits:
                break

            for hit in hits:
                patent = _parse_hit(hit, keyword, domain_tag_map=domain_tag_map)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("Lens | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            offset += _PAGE_SIZE
            if offset >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("Lens | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
