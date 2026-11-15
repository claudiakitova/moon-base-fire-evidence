"""Harvest NASA Technical Reports Server (NTRS) records for the 24 PSI combustion investigations.

Two ways of linking a report to an investigation:
  1. "pub"  - exact title match against a publication listed on the PSI investigation page (high precision)
  2. "name" - phrase search on the investigation's name/acronym (broader; label shows which query hit)

Output (Desktop/personal/nasa/data/ntrs/):
  ntrs_records.json  - one entry per unique NTRS report, with all PSI links and the reason for each
  ntrs_records.csv   - same, flat
  pdfs/<id>.pdf      - full text where NTRS offers a public download
"""
import csv, json, re, sys, time, unicodedata
from pathlib import Path
import requests

BASE = "https://ntrs.nasa.gov"
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "ntrs"
PDFS = OUT / "pdfs"
S = requests.Session()
S.headers["User-Agent"] = "space-apps-research-script"

# Phrase queries per investigation (quoted = exact phrase in NTRS).
NAME_QUERIES = {
    "PSI-10":  ['"Flame Design" ACME', '"Flame Design" microgravity soot'],
    "PSI-20":  ['"Burning Rate Emulator"'],
    "PSI-21":  ['"Coflow Laminar Diffusion Flame"', '"CLD Flame"'],
    "PSI-22":  ['"E-FIELD Flames"', '"Electric-Field Effects on Laminar Diffusion Flames"'],
    "PSI-23":  ['"Structure and Response of Spherical Diffusion Flames"', '"s-Flame"'],
    "PSI-25":  ['"BASS-II"'],
    "PSI-26":  ['"Burning and Suppression of Solids"'],
    "PSI-39":  ['"Cool Flames Investigation"'],
    "PSI-47":  ['"Dust and Aerosol Measurement Feasibility Test"', '"DAFT" aerosol'],
    "PSI-60":  ['"Smoke Point In Co-flow"', '"SPICE" smoke point'],
    "PSI-62":  ['"Flamelet Generated Manifolds" flame spread'],
    "PSI-68":  ['"FLEX-2"'],
    "PSI-69":  ['"Flame Extinguishment Experiment"'],
    "PSI-98":  ['Saffire spacecraft fire', '"Spacecraft Fire Safety Demonstration"', '"Saffire-I"'],
    "PSI-99":  ['Saffire spacecraft fire', '"Saffire-II"'],
    "PSI-100": ['Saffire spacecraft fire', '"Saffire-III"'],
    "PSI-101": ['"Smoke Aerosol Measurement Experiment"', '"SAME-R"'],
    "PSI-102": ['"Smoke and Aerosol Measurement Experiment"', '"Smoke Aerosol Measurement Experiment"'],
    "PSI-106": ['"Structure and Liftoff In Combustion"'],
    "PSI-107": ['"Smoke Point In Co-flow"'],
    "PSI-115": ['"Smoke Aerosol Measurement Experiment" modeling'],
    "PSI-117": ['"cool flame" droplet microgravity'],
    "PSI-142": ['"cool flame" radiation extinction'],
    "PSI-159": ['"Cool Flames Investigation with Gases"', '"CFI-G"'],
}
PAGE = 100
MAX_PER_QUERY = 300  # safety cap for broad queries


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def search(q: str):
    out, start = [], 0
    while start < MAX_PER_QUERY:
        for attempt in range(4):
            r = S.get(f"{BASE}/api/citations/search",
                      params={"q": q, "page.size": PAGE, "page.from": start}, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (attempt + 1)); continue
            r.raise_for_status(); break
        else:
            print(f"   ! gave up on {q!r} at {start}", file=sys.stderr); break
        d = r.json()
        res = d.get("results", [])
        out += res
        start += PAGE
        if start >= d["stats"]["total"] or not res:
            break
        time.sleep(0.5)
    time.sleep(0.5)
    return out


def slim(rec):
    pdf = None
    for dl in rec.get("downloads") or []:
        links = dl.get("links") or {}
        pdf = links.get("pdf") or (links.get("original") if str(links.get("original", "")).lower().endswith(".pdf") else None)
        if pdf:
            break
    pubs = rec.get("publications") or []
    date = (pubs[0].get("publicationDate") if pubs else None) or rec.get("distributionDate") or ""
    return {
        "id": str(rec["id"]),
        "title": rec.get("title", ""),
        "year": date[:4],
        "type": rec.get("stiType", ""),
        "authors": [a["meta"]["author"]["name"] for a in sorted(rec.get("authorAffiliations") or [],
                    key=lambda a: a.get("sequence", 0)) if a.get("meta", {}).get("author")],
        "keywords": rec.get("keywords") or [],
        "abstract": rec.get("abstract", ""),
        "distribution": rec.get("distribution", ""),
        "pdf_url": (BASE + pdf) if pdf and pdf.startswith("/") else pdf,
        "record_url": f"{BASE}/citations/{rec['id']}",
        "links": [],  # filled below: {"psi": .., "acronym": .., "how": "pub"|"name", "query": ..}
    }


def main(download_pdfs=True):
    OUT.mkdir(parents=True, exist_ok=True); PDFS.mkdir(exist_ok=True)
    inv = json.loads((DATA / "psi_combustion_investigations.json").read_text(encoding="utf-8-sig"))
    records = {}

    def add(rec, psi, acr, how, q):
        s = records.setdefault(str(rec["id"]), slim(rec))
        link = {"psi": psi, "acronym": acr, "how": how, "query": q}
        if not any(l["psi"] == psi and l["how"] == how for l in s["links"]):
            s["links"].append(link)

    for i in inv:
        psi, acr = i["Accession"], i.get("Acronym") or ""
        label = acr or i["Title"][:50]
        # 1) exact publication-title matches
        titles = [t.strip() for t in re.split(r"\s{3,}", i.get("Publication Title") or "") if len(t.strip()) > 15]
        hit = 0
        for t in titles:
            nt = norm(t)
            for rec in search(f'"{t[:200]}"')[:10]:
                if norm(rec.get("title")) == nt:
                    add(rec, psi, acr, "pub", t); hit += 1
        # 2) name/acronym phrase queries
        nhit = 0
        for q in NAME_QUERIES.get(psi, []):
            res = search(q)
            for rec in res:
                add(rec, psi, acr, "name", q)
            nhit += len(res)
        print(f"{psi:8} {label:28} pubs listed {len(titles):3} | matched in NTRS {hit:3} | name-search hits {nhit:4}")

    recs = sorted(records.values(), key=lambda r: (r["year"], r["id"]))
    # PDFs
    got = 0
    if download_pdfs:
        for r in recs:
            if not r["pdf_url"]:
                continue
            f = PDFS / f"{r['id']}.pdf"
            if f.exists() and f.stat().st_size > 1000:
                r["pdf_file"] = f"pdfs/{f.name}"; got += 1; continue
            try:
                resp = S.get(r["pdf_url"], timeout=120)
                if resp.ok and resp.content[:4] == b"%PDF":
                    f.write_bytes(resp.content); r["pdf_file"] = f"pdfs/{f.name}"; got += 1
                else:
                    r["pdf_error"] = f"HTTP {resp.status_code}"
            except requests.RequestException as e:
                r["pdf_error"] = type(e).__name__
            time.sleep(1)

    (OUT / "ntrs_records.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(OUT / "ntrs_records.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "year", "type", "title", "authors", "psi_links", "how", "pdf_file", "record_url", "abstract"])
        for r in recs:
            w.writerow([r["id"], r["year"], r["type"], r["title"], "; ".join(r["authors"]),
                        "; ".join(sorted({f'{l["psi"]} {l["acronym"]}'.strip() for l in r["links"]})),
                        "; ".join(sorted({l["how"] for l in r["links"]})),
                        r.get("pdf_file", ""), r["record_url"], r["abstract"]])
    pub_linked = sum(any(l["how"] == "pub" for l in r["links"]) for r in recs)
    print(f"\nunique NTRS reports: {len(recs)} | linked via PSI publication title: {pub_linked} | "
          f"with public PDF url: {sum(bool(r['pdf_url']) for r in recs)} | PDFs saved: {got}")


if __name__ == "__main__":
    main(download_pdfs="--no-pdfs" not in sys.argv)
