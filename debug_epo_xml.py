"""
EPO XML inspector — uses individual patent endpoint (not search)
so it doesn't burn the weekly search quota.

Run:
    python debug_epo_xml.py
"""
import sys, os, xml.etree.ElementTree as ET
sys.path.insert(0, ".")

import requests
from backend.config import EPO_OPS_KEY, EPO_OPS_SECRET

_NS = {
    "ops":   "http://ops.epo.org/3.2",
    "epo":   "http://www.epo.org/exchange",
    "dc":    "http://purl.org/dc/elements/1.1/",
    "xlink": "http://www.w3.org/1999/xlink",
}

# Grab a patent number that's already in your DB
PATENT_NUMBER = "KR20260042123"


def main():
    # ── Auth ────────────────────────────────────────────────────────────────────
    r = requests.post(
        "https://ops.epo.org/3.2/auth/accesstoken",
        data={"grant_type": "client_credentials"},
        auth=(EPO_OPS_KEY, EPO_OPS_SECRET),
        timeout=20,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    print("Auth OK\n")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/xml",
    })

    # ── Individual patent biblio (much cheaper than search) ────────────────────
    url = f"https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc/{PATENT_NUMBER}/biblio"
    r = session.get(url, timeout=30)
    print(f"Status: {r.status_code}")
    if not r.ok:
        print(r.text[:500])
        return

    with open("/tmp/epo_single.xml", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Full XML → /tmp/epo_single.xml\n")

    root = ET.fromstring(r.content)

    # Find exchange-document
    docs = root.findall(".//{http://www.epo.org/exchange}exchange-document")
    if not docs:
        docs = root.findall(".//{http://ops.epo.org/3.2}exchange-document")
    print(f"exchange-document elements found: {len(docs)}\n")

    if not docs:
        print("No docs — dumping root:\n")
        print(ET.tostring(root, encoding="unicode")[:3000])
        return

    doc = docs[0]
    print("── Raw exchange-document (first 3000 chars) ────────────────────────────")
    print(ET.tostring(doc, encoding="unicode")[:3000])
    print("\n")

    biblio = doc.find("epo:bibliographic-data", _NS)
    if biblio is None:
        print("bibliographic-data NOT found with epo: namespace")
        print("Trying no-namespace fallback…")
        biblio = doc.find("bibliographic-data")
        if biblio is None:
            print("Still not found. All child tags of doc:")
            for child in doc:
                print(f"  {child.tag!r}")
            return

    # Title
    title_el = (biblio.find("epo:invention-title[@lang='en']", _NS)
                or biblio.find("epo:invention-title", _NS))
    print(f"title = {(title_el.text or '').strip()!r}\n")

    # Applicants — dump raw XML
    print("── Raw <applicants> block ───────────────────────────────────────────────")
    for tag in [
        "epo:parties/epo:applicants",
        ".//epo:applicants",
        ".//applicants",
    ]:
        el = biblio.find(tag, _NS)
        if el is not None:
            print(f"Found via path {tag!r}:")
            print(ET.tostring(el, encoding="unicode")[:2000])
            break
    else:
        print("No <applicants> block found. Listing all tags in biblio:")
        for child in biblio:
            print(f"  {child.tag!r}")

    print()

    # Probe each applicant
    print("── Each <applicant> element ─────────────────────────────────────────────")
    for path in [".//epo:applicant", ".//applicant"]:
        els = biblio.findall(path, _NS)
        if els:
            print(f"Path {path!r} → {len(els)} element(s)")
            for ap in els:
                print(f"  attribs={ap.attrib}")
                print(f"  raw: {ET.tostring(ap, encoding='unicode')[:500]}")
                print()
            break
    else:
        print("No <applicant> found under biblio")


if __name__ == "__main__":
    main()
