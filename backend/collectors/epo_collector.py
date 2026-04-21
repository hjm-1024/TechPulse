"""
EPO OPS (Open Patent Services) collector.
Provides worldwide patent data including US, KR, EP, WO.

Free tier: 4 GB / week  |  Rate limit: 25 req / 30 sec
Registration: https://developers.epo.org/

Set in .env:
    EPO_OPS_KEY=<Consumer Key>
    EPO_OPS_SECRET=<Consumer Secret>
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Generator

import requests

from backend.config import DOMAIN_TAG_MAP, EPO_OPS_KEY, EPO_OPS_SECRET, KEYWORDS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_AUTH_URL   = "https://ops.epo.org/3.2/auth/accesstoken"
_SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
_BATCH_SIZE = 25          # EPO OPS free tier: max 25 per request
_RATE_LIMIT_SECS = 1.3    # ~23 req/30s, safely under the 25/30s limit
_MAX_RETRIES = 4

_NS = {
    "ops":      "http://ops.epo.org/3.2",
    "epo":      "http://www.epo.org/exchange",
    "dc":       "http://purl.org/dc/elements/1.1/",
    "xlink":    "http://www.w3.org/1999/xlink",
}


# ── Authentication ────────────────────────────────────────────────────────────

def _get_token(session: requests.Session) -> str:
    resp = session.post(
        _AUTH_URL,
        data={"grant_type": "client_credentials"},
        auth=(EPO_OPS_KEY, EPO_OPS_SECRET),
        timeout=20,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token", "")
    if not token:
        raise ValueError("EPO OPS: no access_token in auth response")
    return token


def _make_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "User-Agent": "TechPulse/1.0 (research dashboard)",
        "Accept": "application/xml",
    })
    return session


# ── Query builder ─────────────────────────────────────────────────────────────

def _build_cql(keyword: str, days_back: int) -> str:
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")
    # CQL: title or abstract contains keyword, recent publications
    escaped = keyword.replace('"', '\\"')
    return f'(ti="{escaped}" OR ab="{escaped}") AND pd>={since}'


# ── XML parser ────────────────────────────────────────────────────────────────

def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_document(doc: ET.Element, keyword: str) -> dict | None:
    biblio = doc.find("epo:bibliographic-data", _NS)
    if biblio is None:
        return None

    # Title
    title_el = biblio.find(
        "epo:invention-title[@lang='en']", _NS
    ) or biblio.find("epo:invention-title", _NS)
    title = _text(title_el)
    if not title:
        return None

    # Abstract (may be top-level sibling, not inside biblio)
    abstract = ""
    for ab in doc.findall("epo:abstract", _NS):
        lang = ab.get("lang", "")
        if lang in ("en", "") or not abstract:
            abstract = " ".join(_text(p) for p in ab.findall("epo:p", _NS))
            if lang == "en":
                break

    # Publication reference → patent_number
    pub_ref = biblio.find("epo:publication-reference/epo:document-id[@document-id-type='epodoc']", _NS) \
           or biblio.find("epo:publication-reference/epo:document-id", _NS)
    country   = _text(pub_ref.find("epo:country", _NS))   if pub_ref is not None else ""
    doc_num   = _text(pub_ref.find("epo:doc-number", _NS)) if pub_ref is not None else ""
    kind      = _text(pub_ref.find("epo:kind", _NS))       if pub_ref is not None else ""
    pub_date  = _text(pub_ref.find("epo:date", _NS))       if pub_ref is not None else ""
    # Format date YYYYMMDD → YYYY-MM-DD
    if len(pub_date) == 8:
        pub_date = f"{pub_date[:4]}-{pub_date[4:6]}-{pub_date[6:]}"

    patent_number = f"{country}{doc_num}{kind}".strip()
    if not patent_number:
        return None

    # Filing date
    app_ref = biblio.find(
        "epo:application-reference/epo:document-id[@document-id-type='epodoc']", _NS
    ) or biblio.find("epo:application-reference/epo:document-id", _NS)
    filing_date = _text(app_ref.find("epo:date", _NS)) if app_ref is not None else ""
    if len(filing_date) == 8:
        filing_date = f"{filing_date[:4]}-{filing_date[4:6]}-{filing_date[6:]}"

    # EPO party elements nest the name under <addressbook><name>
    def _party_name(el: ET.Element) -> str:
        return (
            _text(el.find("epo:addressbook/epo:name", _NS))
            or _text(el.find("epo:name", _NS))
        )

    # Inventors — prefer epodoc format (standardised), fall back to any
    inv_els = (
        biblio.findall(".//epo:inventor[@data-format='epodoc']", _NS)
        or biblio.findall(".//epo:inventor", _NS)
    )
    inventors = ", ".join(n for n in (_party_name(i) for i in inv_els) if n)

    # Applicants (assignees) — epodoc format has the Latin-script name
    app_els = (
        biblio.findall(".//epo:applicant[@data-format='epodoc']", _NS)
        or biblio.findall(".//epo:applicant", _NS)
    )
    assignee = "; ".join(n for n in (_party_name(a) for a in app_els) if n)

    # IPC codes — build "H04W" style from section+class+subclass
    ipc_codes = ", ".join(
        filter(None, (
            (
                _text(cl.find("epo:section", _NS))
                + _text(cl.find("epo:class", _NS))
                + _text(cl.find("epo:subclass", _NS))
            ).strip()
            for cl in biblio.findall(".//epo:classification-ipcr", _NS)
        ))
    )

    return {
        "patent_number": patent_number,
        "title": title,
        "abstract": abstract,
        "inventors": inventors,
        "assignee": assignee,
        "filing_date": filing_date,
        "publication_date": pub_date,
        "ipc_codes": ipc_codes,
        "source": "epo",
        "country": country or "WO",
        "domain_tag": DOMAIN_TAG_MAP.get(keyword, "other"),
    }


# ── Fetch with retry ──────────────────────────────────────────────────────────

def _fetch_page(
    cql: str,
    start: int,
    session: requests.Session,
    auth_session: requests.Session,   # for token refresh
) -> tuple[list[ET.Element], int]:
    range_header = f"{start}-{start + _BATCH_SIZE - 1}"
    delay = 2.0

    for attempt in range(_MAX_RETRIES):
        resp = session.get(
            _SEARCH_URL,
            params={"q": cql},
            headers={"X-OPS-Range": range_header},
            timeout=30,
        )

        if resp.status_code == 400:
            # Query syntax error or range out of bounds — stop gracefully
            logger.debug("EPO OPS 400 (range=%s); likely exhausted results", range_header)
            return [], 0

        if resp.status_code == 401:
            # Token expired — refresh once
            logger.info("EPO OPS token expired, refreshing…")
            token = _get_token(auth_session)
            session.headers.update({"Authorization": f"Bearer {token}"})
            continue

        if resp.status_code == 503:
            wait = int(resp.headers.get("Retry-After", delay))
            logger.warning("EPO OPS throttled (attempt %d); sleeping %ds", attempt + 1, wait)
            time.sleep(wait)
            delay *= 2
            continue

        if resp.status_code >= 500:
            logger.warning("EPO OPS server error %d (attempt %d); sleeping %.0fs",
                           resp.status_code, attempt + 1, delay)
            time.sleep(delay)
            delay *= 2
            continue

        resp.raise_for_status()

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            logger.error("EPO OPS XML parse error: %s", exc)
            return [], 0

        # Total count: try header first, then XML ops:biblio-search/@total
        total = int(resp.headers.get("X-OPS-Total-Count", 0))
        if not total:
            search_el = root.find("ops:biblio-search", _NS)
            if search_el is not None:
                total = int(search_el.get("total-result-count", 0))

        docs = root.findall(".//{http://www.epo.org/exchange}exchange-document")
        if not docs:
            docs = root.findall(".//{http://ops.epo.org/3.2}exchange-document")

        logger.debug("EPO OPS page: docs=%d total=%d", len(docs), total)
        return docs, total

    raise requests.RequestException(f"EPO OPS: gave up after {_MAX_RETRIES} retries")


# ── Public interface ──────────────────────────────────────────────────────────

def fetch_patents(
    keywords: list[str] | None = None,
    days_back: int = 365,
    max_per_keyword: int = 500,
) -> Generator[dict, None, None]:
    """Yield worldwide patent dicts. Skips if EPO_OPS_KEY/SECRET not set."""
    if not EPO_OPS_KEY or not EPO_OPS_SECRET:
        logger.warning(
            "EPO_OPS_KEY or EPO_OPS_SECRET not set in .env — skipping EPO collection. "
            "Register free at https://developers.epo.org/"
        )
        return

    if keywords is None:
        keywords = KEYWORDS

    # Separate plain-requests session for auth (no Bearer header)
    auth_session = requests.Session()
    auth_session.headers.update({"User-Agent": "TechPulse/1.0"})

    try:
        token = _get_token(auth_session)
    except Exception as exc:
        logger.error("EPO OPS auth failed: %s", exc)
        return

    session = _make_session(token)

    for keyword in keywords:
        cql = _build_cql(keyword, days_back)
        logger.info("EPO OPS | keyword=%r | cql=%s", keyword, cql)

        start = 1     # EPO OPS ranges are 1-based
        fetched = 0

        while fetched < max_per_keyword:
            try:
                docs, total = _fetch_page(cql, start, session, auth_session)
            except requests.RequestException as exc:
                logger.error("EPO OPS fetch failed (keyword=%r, start=%d): %s", keyword, start, exc)
                break

            if not docs:
                break

            for doc in docs:
                patent = _parse_document(doc, keyword)
                if patent:
                    yield patent
                    fetched += 1

            logger.debug("EPO OPS | keyword=%r | fetched=%d / total=%d", keyword, fetched, total)

            start += _BATCH_SIZE
            # Stop if we got a partial batch (end of results) or exceeded limits
            if len(docs) < _BATCH_SIZE:
                break
            if total and start > min(total, max_per_keyword):
                break

            time.sleep(_RATE_LIMIT_SECS)

        logger.info("EPO OPS | keyword=%r | done, yielded %d patents", keyword, fetched)
        time.sleep(_RATE_LIMIT_SECS)
