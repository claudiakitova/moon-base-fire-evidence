"""One row per PSI combustion investigation -> data/derived/investigations.csv (+ publications.csv)

Sources (all public):
  - PSI search API records          data/psi_combustion_investigations.json
  - PSI file inventory              data/psi_files/manifest.csv           (psi_files.py --list)
  - NTRS links                      data/ntrs/ntrs_records.json           (ntrs_harvest.py)
  - DataCite (DOI per PSI record)   api.datacite.org, prefix 10.60555, matched on the PSI landing-page URL
Nothing here is typed by hand: every field is copied or counted from those sources.
"""
import collections, csv, json, re
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "derived"
PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{}"
RUN_TABLES = {"PSI-25": "runs_bass.csv", "PSI-26": "runs_bass.csv"}


def dois():
    out, url = {}, "https://api.datacite.org/dois?query=prefix:10.60555&page[size]=200"
    while url:
        d = requests.get(url, headers={"User-Agent": "space-apps-research-script"}, timeout=60).json()
        for x in d["data"]:
            m = re.search(r"(PSI-\d+)$", x["attributes"].get("url") or "")
            if m:
                out[m.group(1)] = x["id"]
        url = d.get("links", {}).get("next")
    return out


def clean(s, n=None):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n].rsplit(" ", 1)[0] + "…" if n and len(s) > n else s


def split_multi(s):
    return [t.strip() for t in re.split(r"\s{3,}", str(s or "")) if t.strip()]


def main():
    OUT.mkdir(exist_ok=True)
    inv = json.loads((DATA / "psi_combustion_investigations.json").read_text(encoding="utf-8-sig"))
    man = list(csv.DictReader(open(DATA / "psi_files" / "manifest.csv", encoding="utf-8-sig")))
    files = collections.defaultdict(list)
    for r in man:
        files[r["psi"]].append(r)
    ntrs = json.loads((DATA / "ntrs" / "ntrs_records.json").read_text(encoding="utf-8"))
    doi = dois()

    rows, pubs = [], []
    for i in sorted(inv, key=lambda x: int(x["Accession"][4:])):
        psi = i["Accession"]
        fs = files.get(psi, [])
        ext = collections.Counter(f["ext"] for f in fs)
        hw = i.get("Experiment Hardware")
        hw = hw.get("Name") if isinstance(hw, dict) else "; ".join(h.get("Name", "") for h in hw) if isinstance(hw, list) else hw
        person = i.get("Person") or {}
        linked = [n for n in ntrs if any(l["psi"] == psi for l in n["links"])]
        certain = [n for n in linked if any(l["psi"] == psi and l["how"] == "pub" for l in n["links"])]
        rows.append({
            "psi": psi, "acronym": i.get("Acronym") or "", "title": clean(i.get("Title")),
            "doi": doi.get(psi, ""), "psi_page": PSI_PAGE.format(psi),
            "project_type": i.get("Project Type", ""), "subresearch_area": i.get("SubResearch Area", ""),
            "flight_platform": i.get("Flight Platform", ""), "hardware": clean(hw),
            "start": i.get("Investigation Start Date", ""), "end": i.get("Investigation End Date", ""),
            "pi": clean(f"{person.get('First Name', '')} {person.get('Middle Initials', '')} {person.get('Last Name', '')}"),
            "related_investigations": ", ".join(split_multi(i.get("Related Investigations"))),
            "keywords": "; ".join(split_multi(i.get("Keywords"))),
            "objectives": clean(i.get("Objectives"), 600), "earth_benefits": clean(i.get("Research Impacts/Earth Benefits"), 400),
            "publications_listed_in_psi": len(split_multi(i.get("Publication Title"))),
            "ntrs_reports_linked": len(linked), "ntrs_reports_certain": len(certain),
            "psi_files": len(fs), "psi_total_gb": round(sum(float(f["mb"]) for f in fs) / 1024, 1),
            "psi_spreadsheets_csv": sum(ext[e] for e in (".xlsx", ".xls", ".csv")),
            "psi_videos_images": sum(ext[e] for e in (".mp4", ".avi", ".mov", ".tif", ".tiff", ".jpg", ".png", ".bmp")),
            "run_level_table": RUN_TABLES.get(psi, ""),
        })
        for t in split_multi(i.get("Publication Title")):
            match = next((n for n in certain if any(l["query"] == t for l in n["links"] if l["psi"] == psi)), None)
            pubs.append({"psi": psi, "acronym": i.get("Acronym") or "", "title": t,
                         "ntrs_id": match["id"] if match else "", "ntrs_url": match["record_url"] if match else "",
                         "year": match["year"] if match else ""})

    for name, data in (("investigations.csv", rows), ("publications.csv", pubs)):
        with open(OUT / name, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    print(f"investigations: {len(rows)} | with DOI: {sum(bool(r['doi']) for r in rows)} | publications: {len(pubs)} "
          f"({sum(bool(p['ntrs_id']) for p in pubs)} matched to NTRS)")
    for r in rows:
        print(f"  {r['psi']:8} {r['acronym'][:20]:20} doi={r['doi']:22} files={r['psi_files']:6} {r['psi_total_gb']:8} GB  "
              f"sheets={r['psi_spreadsheets_csv']:4} pubs={r['publications_listed_in_psi']:3} ntrs={r['ntrs_reports_linked']}")


if __name__ == "__main__":
    main()
