"""List and download the small, analysis-ready files (tables + documents) of every PSI combustion investigation.

Uses the same public endpoints the PSI investigation page calls in the browser:
  POST /geode-py/ws/files/v2                    -> file tree   {"fileType":"study","studyId":..,"version":..}
  GET  /geode-py/ws/studies/<id>/download?file= -> short-lived download link (file = bare file name)

Skips raw video/images/archives (hundreds of GB). Output:
  data/psi_files/<PSI-id>/<file>          downloaded files
  data/psi_files/manifest.csv             every file PSI lists (downloaded or not), with size and folder
"""
import csv, json, sys, time
from pathlib import Path
from urllib.parse import quote
import requests

API = "https://psi.nasa.gov/geode-py/ws"
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "psi_files"
S = requests.Session()
S.headers["User-Agent"] = "space-apps-research-script"

WANT_EXT = {".xlsx", ".xls", ".csv", ".txt", ".dat", ".docx", ".doc", ".pdf", ".json", ".xml", ".tsv"}
MAX_MB = 60


def file_tree(psi):
    """Return (version, flat file list) for the newest version that answers."""
    best = None
    for v in range(1, 11):
        r = S.post(f"{API}/files/v2", json={"folder": "", "fileType": "study", "studyId": psi, "version": str(v)}, timeout=120)
        try:
            d = r.json()
        except ValueError:
            break
        if "files" not in d:
            if best:
                break
            continue
        best = (v, d["files"])
        time.sleep(0.5)
    if not best:
        return None, []
    flat = []

    def walk(nodes):
        for n in nodes:
            if n.get("directory") is False and n.get("key"):
                flat.append(n)
            walk(n.get("files") or [])
    walk(best[1])
    # the tree repeats some files under several categories; keep one per key
    seen, uniq = set(), []
    for f in flat:
        if f["key"] not in seen:
            seen.add(f["key"]); uniq.append(f)
    return best[0], uniq


def download(psi, version, f, dest):
    name = f["key"].rsplit("/", 1)[-1]
    r = S.get(f"{API}/studies/{psi}/download?file={quote(name)}&version={f.get('version', 1)}"
              f"&studyVersion={version}&redirect=false", timeout=60)
    link = r.text.strip().strip('"')
    if not link.startswith("http"):
        return f"no link: {link[:80]}"
    resp = S.get(link, timeout=600)
    if not resp.ok:
        return f"HTTP {resp.status_code}"
    dest.write_bytes(resp.content)
    return "ok"


def main(only=None):
    inv = json.loads((DATA / "psi_combustion_investigations.json").read_text(encoding="utf-8-sig"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in inv:
        psi, acr = i["Accession"], i.get("Acronym") or ""
        if only and psi not in only:
            continue
        version, files = file_tree(psi)
        total_gb = sum(f.get("bytes_size", 0) for f in files) / 2**30
        got = skipped = 0
        for f in files:
            name = f["key"].rsplit("/", 1)[-1]
            folder = "/".join(f["key"].split("/")[2:-1])
            ext = Path(name).suffix.lower()
            mb = f.get("bytes_size", 0) / 2**20
            status = "skipped (type/size)"
            if f.get("restricted") or f.get("restrictedAccess"):
                status = "restricted"
            elif LIST_ONLY:
                status = "listed"
            elif ext in WANT_EXT and mb <= MAX_MB:
                sub = OUT / psi / folder
                sub.mkdir(parents=True, exist_ok=True)
                dest = sub / name
                if dest.exists() and dest.stat().st_size > 0:
                    status = "ok (cached)"
                else:
                    try:
                        status = download(psi, version, f, dest)
                    except requests.RequestException as e:
                        status = type(e).__name__
                    time.sleep(0.5)
            if status.startswith("ok"):
                got += 1
            else:
                skipped += 1
            rows.append({"psi": psi, "acronym": acr, "study_version": version, "folder": folder, "file": name,
                         "ext": ext, "mb": round(mb, 3), "status": status,
                         "local": str((OUT / psi / folder / name).relative_to(DATA)) if status.startswith("ok") else ""})
        print(f"{psi:8} {acr[:22]:22} v{version}  files {len(files):5}  total {total_gb:8.1f} GB  downloaded {got:4}  skipped {skipped:5}", flush=True)
    mname = "manifest.csv" if not only else f"manifest_{'_'.join(sorted(only))}.csv"
    with open(OUT / mname, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r["status"].startswith("ok")]
    print(f"\ndownloaded {len(ok)} files, {sum(r['mb'] for r in ok):.1f} MB | errors: "
          f"{sum(1 for r in rows if not r['status'].startswith(('ok', 'skipped', 'restricted')))}")


LIST_ONLY = "--list" in sys.argv

if __name__ == "__main__":
    main(set(a for a in sys.argv[1:] if not a.startswith("--")) or None)
