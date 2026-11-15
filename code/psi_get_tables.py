"""Download only the run tables / test logs / readmes picked from manifest.csv (made by psi_files.py --list).

Rule: candidate tables (xlsx/xls, or csv/doc/txt/pdf named like matrix/table/summary/log/readme...)
      of <= 3 MB, plus every Saffire spreadsheet/readme (their merge results are the main flame-spread data).
Also removes files under data/psi_files/<PSI> that are not in the pick list (left over from the first, too-broad run).
"""
import csv, re, sys, time
from pathlib import Path
import psi_files as pf

OUT = pf.OUT
pat = re.compile(r"matrix|experiment.?table|test.?table|run.?table|summary|log|conditions|test.?list|parameters|index|overview|readme", re.I)


def picked(r):
    mb, ext = float(r["mb"]), r["ext"]
    if ext not in (".xlsx", ".xls", ".csv", ".docx", ".doc", ".txt", ".pdf"):
        return False
    if not (ext in (".xlsx", ".xls") or pat.search(r["file"])):
        return False
    if r["psi"] in ("PSI-98", "PSI-99", "PSI-100"):
        return mb <= 25
    return mb <= 3


def main():
    rows = list(csv.DictReader(open(OUT / "manifest.csv", encoding="utf-8-sig")))
    picks = [r for r in rows if picked(r)]
    keep = {(OUT / r["psi"] / r["folder"] / r["file"]).resolve() for r in picks}
    # clean leftovers
    freed = 0
    for f in OUT.glob("PSI-*/**/*"):
        if f.is_file() and f.resolve() not in keep:
            freed += f.stat().st_size; f.unlink()
    for d in sorted(OUT.glob("PSI-*/**/"), key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    print(f"removed leftovers: {freed/2**20:.0f} MB")
    print(f"to fetch: {len(picks)} files, {sum(float(r['mb']) for r in picks):.0f} MB", flush=True)
    status_rows, done = [], 0
    for r in picks:
        dest = OUT / r["psi"] / r["folder"] / r["file"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            st = "ok (cached)"
        else:
            try:
                st = pf.download(r["psi"], r["study_version"], {"key": f"x/x/{r['file']}"}, dest)
            except Exception as e:
                st = type(e).__name__
            time.sleep(0.4)
        done += 1
        if done % 50 == 0:
            print(f"  {done}/{len(picks)}", flush=True)
        status_rows.append({**r, "status": st, "local": str(dest.relative_to(pf.DATA)) if st.startswith("ok") else ""})
    with open(OUT / "tables_manifest.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(status_rows[0].keys())); w.writeheader(); w.writerows(status_rows)
    bad = [s for s in status_rows if not s["status"].startswith("ok")]
    print(f"done: {len(status_rows) - len(bad)} ok, {len(bad)} failed")
    for s in bad[:15]:
        print("  FAIL", s["psi"], s["file"], s["status"])


if __name__ == "__main__":
    main()
