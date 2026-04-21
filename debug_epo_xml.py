"""
One-shot EPO XML inspector. Run:
    python debug_epo_xml.py
Prints the first exchange-document's raw XML and probes the party-name paths.
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

    # ── Fetch 3 results ─────────────────────────────────────────────────────────
    r = session.get(
        "https://ops.epo.org/3.2/rest-services/published-data/search/biblio",
        params={"q": 'ti="humanoid robot"'},
        headers={"X-OPS-Range": "1-3"},
        timeout=30,
    )
    r.raise_for_status()

    # Save full response for manual inspection
    with open("/tmp/epo_sample.xml", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Full XML saved → /tmp/epo_sample.xml\n")

    root = ET.fromstring(r.content)

    # Find exchange-documents using both namespace variants
    docs = root.findall(".//{http://www.epo.org/exchange}exchange-document")
    if not docs:
        docs = root.findall(".//{http://ops.epo.org/3.2}exchange-document")
    print(f"Found {len(docs)} exchange-document(s)\n")
    if not docs:
        print("ERROR: no docs found. Dumping root:\n")
        print(ET.tostring(root, encoding="unicode")[:3000])
        return

    doc = docs[0]
    print("── First exchange-document (raw XML, first 3000 chars) ────────────────")
    print(ET.tostring(doc, encoding="unicode")[:3000])
    print("\n")

    biblio = doc.find("epo:bibliographic-data", _NS)
    if biblio is None:
        print("ERROR: bibliographic-data not found")
        return

    # ── Title ───────────────────────────────────────────────────────────────────
    title_el = biblio.find("epo:invention-title[@lang='en']", _NS) \
             or biblio.find("epo:invention-title", _NS)
    print(f"title = {(title_el.text or '').strip()!r}\n")

    # ── Applicants ──────────────────────────────────────────────────────────────
    print("── All <applicant> elements ────────────────────────────────────────────")
    for ap in biblio.findall(".//epo:applicant", _NS):
        print(f"  tag={ap.tag!r}  attribs={ap.attrib}")
        print(f"  raw: {ET.tostring(ap, encoding='unicode')[:400]}")
        print()

    # ── Inventors ───────────────────────────────────────────────────────────────
    print("── All <inventor> elements ─────────────────────────────────────────────")
    for inv in biblio.findall(".//epo:inventor", _NS):
        print(f"  tag={inv.tag!r}  attribs={inv.attrib}")
        print(f"  raw: {ET.tostring(inv, encoding='unicode')[:400]}")
        print()

    # ── Probe individual name paths ─────────────────────────────────────────────
    print("── Name path probes (on first applicant, if any) ───────────────────────")
    app_els = biblio.findall(".//epo:applicant", _NS)
    if app_els:
        a = app_els[0]
        for path in [
            "epo:applicant-name/epo:name",
            "epo:inventor-name/epo:name",
            "epo:addressbook/epo:name",
            "epo:name",
            "applicant-name/name",     # no namespace
            "name",                    # bare
        ]:
            el = a.find(path, _NS)
            val = (el.text or "").strip() if el is not None else None
            print(f"  find({path!r}) → {val!r}")

if __name__ == "__main__":
    main()
