"""
KIPRIS collector — Korean Intellectual Property Rights Information Service.

API key required: register at https://www.data.go.kr (무료)
Set KIPRIS_API_KEY in .env after registration.

Endpoint: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, KEYWORDS
from backend.utils.logger import get_logger

try:
    from backend.config import KIPRIS_API_KEY
except ImportError:
    KIPRIS_API_KEY = ""

logger = get_logger(__name__)

_BASE_URL = "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/applicationNumberSearchInfo"
_PAGE_SIZE = 100
_RATE_LIMIT_SECS = 1.0
_MAX_RETRIES = 4

# KIPRIS IPC keyword search endpoint
_SEARCH_URL = "http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/wordSearchInfo"


def _build_params(keyword: str, page: int, days_back: int) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return {
        "ServiceKey": KIPRIS_API_KEY,
        "word": keyword,
        "docsStart": (page - 1) * _PAGE_SIZE + 1,
        "docsCount": _PAGE_SIZE,
        "applicationDate": f"{since}~{today}",
        "patent": "true",
        "utility": "false",
    }


def _parse_item(item: ET.Element, keyword: str, domain_tag_map=None) -> dict | None:
    def _text(tag: str) -> str:
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    title = _text("inventionTitle")
    if not title:
        return None

    abstract = _text("astrtCont")
    inventors = _text("inventorName")
    assignee = _text("applicantName")
    app_number = _text("applicationNumber")
    pub_number = _text("publicationNumber") or _text("registerNumber")
    app_date = _text("applicationDate")
    pub_date = _text("publicationDate") or _text("registerDate")
    ipc_codes = _text("ipcNumber")

    return {
        "patent_number": pub_number or app_number,
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": app_date,
        "publication_date": pub_date,
        "ipc_codes": ipc_codes,
        "source": "kipris",
        "country": "KR",
        "domain_tag": (domain_tag_map or DOMAIN_TAG_MAP).get(keyword, "other"),
    }


def _fetch_page(keyword: str, page: int, days_back: int, session: requests.Session) -> tuple[list[ET.Element], int]:
    params = _build_params(keyword, page, days_back)
    delay = 2.0

    for attempt in range(_MAX_RETRIES):
        resp = session.get(_SEARCH_URL, params=params, timeout=30)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("KIPRIS rate-limited (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("KIPRIS server error %d (attempt %d); sleeping %.0fs", resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            logger.error("KIPRIS XML parse error: %s", exc)
            return [], 0

        # Check for API error in response
        err = root.find(".//errMsg")
        if err is not None and err.text:
            logger.error("KIPRIS API error: %s", err.text)
            return [], 0

        items = root.findall(".//item")
        try:
            total = int((root.find(".//totalCount") or root.find(".//count") or ET.Element("x")).text or 0)
        except (ValueError, AttributeError):
            total = len(items)

        return items, total

    raise requests.RequestException(f"KIPRIS: gave up after {_MAX_RETRIES} retries")


def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
    domain_tag_map: dict | None = None,
) -> Generator[dict, None, None]:
    """Yield Korean patent dicts. Skipped entirely if KIPRIS_API_KEY is not set."""
    if not KIPRIS_API_KEY:
        logger.warning(
            "KIPRIS_API_KEY not set in .env — skipping KIPRIS collection. "
            "Register at https://www.data.go.kr to get a free key."
        )
        return

    if keywords is None:
        keywords = KEYWORDS

    session = requests.Session()
    session.headers.update({"User-Agent": "TechPulse/1.0 (research dashboard)"})

    for keyword in keywords:
        logger.info("KIPRIS | keyword=%r | days_back=%d", keyword, days_back)

        page = 1
        fetched = 0

        while fetched < max_per_keyword:
            try:
                items, total = _fetch_page(keyword, page, days_back, session)
            except requests.RequestException as exc:
                logger.error("KIPRIS fetch failed (keyword=%r, page=%d): %s", keyword, page, exc)
                break

            if not items:
                break

            for item in items:
                patent = _parse_item(item, keyword, domain_tag_map=domain_tag_map)
                if patent and patent["patent_number"]:
                    yield patent
                    fetched += 1

            logger.debug("KIPRIS | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            if page * _PAGE_SIZE >= min(total, max_per_keyword):
                break

            page += 1
            time.sleep(_RATE_LIMIT_SECS)

        logger.info("KIPRIS | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
