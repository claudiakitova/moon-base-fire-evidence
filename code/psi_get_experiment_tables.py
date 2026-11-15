"""Download PSI's official 'Experimental table' CSVs (one or two per investigation) into data/psi_files/<PSI>/Experimental table/."""
import csv, time
import psi_files as pf

rows = [r for r in csv.DictReader(open(pf.OUT / "manifest.csv", encoding="utf-8-sig")) if r["folder"] == "Experimental table"]
ok = 0
for r in rows:
    dest = pf.OUT / r["psi"] / r["folder"] / r["file"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    st = "ok (cached)" if dest.exists() and dest.stat().st_size else pf.download(r["psi"], r["study_version"], {"key": f"x/x/{r['file']}"}, dest)
    ok += st.startswith("ok")
    print(f"{r['psi']:8} {st:12} {r['file']}")
    time.sleep(0.4)
print(f"{ok}/{len(rows)} downloaded")
