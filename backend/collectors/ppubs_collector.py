"""
USPTO PPUBS collector — uses the REST API powering https://ppubs.uspto.gov.

Flow:
  1. POST /users/me/session  → establish session (gets CSRF/cookie)
  2. POST /searches          → submit query, returns results + queryId
  3. Paginate via start offset in subsequent POSTs

No API key required. Field codes: TTL/=title, ABST/=abstract.
"""

import time
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_BASE       = "https://ppubs.uspto.gov/dirsearch-public"
_SESSION    = f"{_BASE}/users/me/session"
_SEARCH     = f"{_BASE}/searches"

_PAGE_SIZE       = 25
_RATE_LIMIT_SECS = 1.2
_MAX_RETRIES     = 4

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://ppubs.uspto.gov",
    "Referer": "https://ppubs.uspto.gov/",
    "Content-Type": "application/json",
}


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        r = session.post(_SESSION, json={}, timeout=15)
        logger.debug("PPUBS session: HTTP %d", r.status_code)
    except Exception as exc:
        logger.warning("PPUBS session init failed (continuing): %s", exc)
    return session


def _build_payload(keyword: str, days_back: int, start: int) -> dict:
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%m-%d-%Y")
    today = datetime.utcnow().strftime("%m-%d-%Y")
    escaped = keyword.replace('"', '\\"')
    return {
        "query": f'(TTL/"{escaped}" OR ABST/"{escaped}")',
        "start": start,
        "pageCount": _PAGE_SIZE,
        "sort": "date_publ desc",
        "dateRange": "custom",
        "startDate": since,
        "endDate": today,
        "dbIds": ["US-PGPUB", "USPAT"],
        "queryId": 0,
        "domainId": 0,
    }


def _parse_patent(item: dict, keyword: str) -> dict | None:
    title = (
        item.get("title") or item.get("inventionTitle") or item.get("patent_title") or ""
    ).strip()
    if not title:
        return None

    abstract = (item.get("abstract") or item.get("abstractText") or "").replace("\n", " ").strip()

    patent_number = (
        item.get("patentNumber") or item.get("documentNumber")
        or item.get("guid") or item.get("applicationNumber") or ""
    ).strip()
    if not patent_number:
        return None

    def _fmt(d: str) -> str:
        d = d.replace("-", "").replace("/", "")
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d

    pub_date  = _fmt(item.get("publicationDate") or item.get("date_publ") or "")
    file_date = _fmt(item.get("filingDate") or item.get("applicationDate") or "")

    inv_raw = item.get("inventors") or item.get("inventorList") or []
    inventors = ", ".join(
        (i.get("name") or f"{i.get('firstName','')} {i.get('lastName','')}").strip()
        for i in inv_raw if isinstance(i, dict)
    ) if isinstance(inv_raw, list) else str(inv_raw)

    asg_raw = item.get("assignees") or item.get("applicants") or []
    assignee = "; ".join(
        (a.get("name") or a.get("orgName") or "").strip()
        for a in asg_raw if isinstance(a, dict)
    ) if isinstance(asg_raw, list) else str(asg_raw)

    ipc_raw = item.get("ipcCodes") or item.get("classifications") or []
    ipc_codes = ", ".join(str(c) for c in ipc_raw[:5]) if isinstance(ipc_raw, list) else str(ipc_raw)

    return {
        "patent_number": patent_number,
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": file_date,
        "publication_date": pub_date,
        "ipc_codes": ipc_codes,
        "source": "uspto",
        "country": "US",
        "domain_tag": DOMAIN_TAG_MAP.get(keyword, "other"),
    }


def _fetch_page(payload: dict, session: requests.Session) -> tuple[list[dict], int]:
    delay = 2.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = session.post(_SEARCH, json=payload, timeout=30)
        except requests.RequestException as exc:
            logger.warning("PPUBS request error (attempt %d): %s", attempt + 1, exc)
            time.sleep(delay); delay *= 2
            continue

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("PPUBS rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait); delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("PPUBS %d (attempt %d); sleeping %.0fs", resp.status_code, attempt + 1, delay)
            time.sleep(delay); delay *= 2
            continue

        if not resp.ok:
            logger.error("PPUBS HTTP %d — URL: %s — body: %s",
                         resp.status_code, _SEARCH, resp.text[:400])
            return [], 0

        try:
            data = resp.json()
        except Exception:
            logger.error("PPUBS non-JSON: %s", resp.text[:200])
            return [], 0

        # Try multiple response shapes
        if isinstance(data, list):
            return data, len(data)

        total = (
            data.get("totalCount") or data.get("total")
            or (data.get("hits") or {}).get("total") or 0
        )
        items = (
            data.get("patents") or data.get("results") or data.get("documents")
            or (data.get("hits") or {}).get("hits") or []
        )

        # Log full response once for debugging if empty
        if not items and attempt == 0:
            logger.debug("PPUBS response keys: %s | body[:300]: %s",
                         list(data.keys()) if isinstance(data, dict) else type(data),
                         str(data)[:300])

        return items, int(total)

    raise requests.RequestException(f"PPUBS: gave up after {_MAX_RETRIES} retries")


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
) -> Generator[dict, None, None]:
    if keywords is None:
        keywords = KEYWORDS

    session = _make_session()

    for keyword in keywords:
        logger.info("PPUBS | keyword=%r | days_back=%d", keyword, days_back)

        page = 0
        fetched = 0

        while fetched < max_per_keyword:
            payload = _build_payload(keyword, days_back, page * _PAGE_SIZE)
            try:
                items, total = _fetch_page(payload, session)
            except requests.RequestException as exc:
                logger.error("PPUBS failed (keyword=%r): %s", keyword, exc)
                break

            if not items:
                break

            for item in items:
                patent = _parse_patent(item, keyword)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("PPUBS | keyword=%r | page=%d | fetched=%d / total=%d",
                         keyword, page, fetched, total)

            page += 1
            if page * _PAGE_SIZE >= min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("PPUBS | keyword=%r | done, yielded %d", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
