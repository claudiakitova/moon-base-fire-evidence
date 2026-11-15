"""BASS (PSI-26) + BASS-II (PSI-25) run tables -> one tidy table, data/derived/runs_bass.csv

Every value is copied or parsed from the PSI spreadsheets; nothing is invented.
- flow: the "Air display" column. BASS shutter notes pair it with cm/s ("1/25s 10 cm/s"), so it is read as cm/s.
  It is often a sequence (the crew stepped flow down until extinction): we keep the raw text, the first value and the min.
- o2: BASS stores a fraction (0.221) -> converted to %. BASS-II stores % already ("calibrated initial O2").
- pressure: BASS has "pressure, atm"; BASS-II has no pressure column -> left empty (not assumed).
- extinguished: True if the observation/flow text mentions extinction/blowoff; empty if nothing is said.
"""
import csv, re
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent / "data"
SRC = ROOT / "psi_files"
OUT = ROOT / "derived"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
EXT = re.compile(r"\bext(?:ing|inct|\b)|extinguish|blow\s*-?off|blowoff|would not stay lit|went out", re.I)

COLS = ["investigation", "psi", "run_id", "date", "pi_sheet", "material_raw", "material_family", "geometry",
        "thickness_mm", "width_cm", "o2_pct_initial", "o2_pct_final", "pressure_atm", "flow_cm_s_first",
        "flow_cm_s_min", "flow_raw", "extinguished", "co_ppm_final", "co2_final", "observations",
        "gravity", "source_file", "source_sheet"]


def nums(v):
    return [float(x) for x in NUM.findall(str(v or ""))]


def first(v):
    n = nums(v)
    return n[0] if n else ""


def family(m):
    m = (m or "").lower()
    for key, fam in [("pmma", "PMMA (acrylic)"), ("rod", "PMMA (acrylic)"), ("sibal", "SIBAL (cotton-fiberglass fabric)"),
                     ("nomex", "Nomex (aramid fabric)"), ("candle", "wax candle"), ("wax", "wax"), ("delrin", "Delrin (POM)"),
                     ("paper", "paper"), ("ultem", "Ultem"), ("silicone", "silicone"), ("cotton", "cotton")]:
        if key in m:
            return fam
    if any(g in m for g in ("film", "sphere", "spherical")):
        return "PMMA (likely; row names only the shape)"
    return "other"


def geometry(m):
    m = (m or "").lower()
    for g in ("sphere", "rod", "film", "slab", "candle", "cylinder", "flat", "plate"):
        if g in m:
            return g
    if "spherical" in m:
        return "sphere section"
    return ""


def thickness_mm(m):
    m = (m or "").lower()
    if x := re.search(r"(\d+(?:\.\d+)?)\s*(?:micron|µm|um)\b", m):
        return float(x.group(1)) / 1000
    if x := re.search(r"(\d+(?:\.\d+)?)\s*mm\b", m):
        return float(x.group(1))
    if x := re.search(r"(\d+)/(\d+)\s*\"", m):          # rod diameter in inches, e.g. 1/4"
        return round(float(x.group(1)) / float(x.group(2)) * 25.4, 2)
    if x := re.search(r"(0?\.\d+)\s*\"", m):
        return round(float(x.group(1)) * 25.4, 2)
    return ""


def width_cm(m):
    x = re.search(r"(\d+(?:\.\d+)?)\s*cm\b", (m or "").lower())
    return float(x.group(1)) if x else ""


def flows(v):
    n = [x for x in nums(v) if 0 <= x <= 60]   # cm/s range of the duct; drops stray numbers like pot settings > 60
    return (n[0], min(n)) if n else ("", "")


def ext_flag(*texts):
    t = " ".join(str(x or "") for x in texts)
    return True if EXT.search(t) else ""


def bass():
    f = next(SRC.glob("PSI-26/**/*As Run*"))
    ws = openpyxl.load_workbook(f, read_only=True, data_only=True)["as run matrix"]
    rows = list(ws.iter_rows(values_only=True))
    out = []
    for r in rows[3:]:
        if not r or r[2] in (None, "") or not str(r[2]).strip().isdigit():
            continue
        mat = str(r[5] or "").strip()
        o2 = first(r[26]); o2 = round(o2 * 100, 2) if o2 != "" and o2 < 1 else o2
        f1, fmin = flows(r[10])
        out.append({"investigation": "BASS", "psi": "PSI-26", "run_id": f"BASS-{r[2]}", "date": str(r[0])[:10],
                    "pi_sheet": "", "material_raw": mat, "material_family": family(mat), "geometry": geometry(mat),
                    "thickness_mm": thickness_mm(mat), "width_cm": width_cm(mat), "o2_pct_initial": o2,
                    "o2_pct_final": "", "pressure_atm": first(r[27]), "flow_cm_s_first": f1, "flow_cm_s_min": fmin,
                    "flow_raw": str(r[10] or "").strip(), "extinguished": ext_flag(r[29], r[9], r[10]),
                    "co_ppm_final": "", "co2_final": first(r[28]), "observations": str(r[29] or "").strip(),
                    "gravity": "microgravity (ISS, MSG)", "source_file": f.name, "source_sheet": "as run matrix"})
    return out


def bass2():
    f = next(SRC.glob("PSI-25/**/*Test.Matrices*"))
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        for r in rows[1:]:
            if not r or not r[2]:
                continue
            mat = str(r[4] or "").strip()
            f1, fmin = flows(r[7])
            out.append({"investigation": "BASS-II", "psi": "PSI-25", "run_id": f"BASS-II-{r[2]}", "date": str(r[0])[:10],
                        "pi_sheet": ws.title, "material_raw": mat, "material_family": family(mat), "geometry": geometry(mat),
                        "thickness_mm": thickness_mm(mat), "width_cm": width_cm(mat), "o2_pct_initial": first(r[10]),
                        "o2_pct_final": first(r[11]), "pressure_atm": "", "flow_cm_s_first": f1, "flow_cm_s_min": fmin,
                        "flow_raw": str(r[7] or "").strip(), "extinguished": ext_flag(r[6], r[7]),
                        "co_ppm_final": first(r[15]), "co2_final": first(r[13]), "observations": "",
                        "gravity": "microgravity (ISS, MSG)", "source_file": f.name, "source_sheet": ws.title})
    return out


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    runs = bass() + bass2()
    with open(OUT / "runs_bass.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(runs)
    import collections
    print(f"runs: {len(runs)}  ->  {OUT / 'runs_bass.csv'}")
    for inv in ("BASS", "BASS-II"):
        rs = [r for r in runs if r["investigation"] == inv]
        o2 = [r["o2_pct_initial"] for r in rs if r["o2_pct_initial"] != ""]
        p = [r["pressure_atm"] for r in rs if r["pressure_atm"] != ""]
        fl = [r["flow_cm_s_first"] for r in rs if r["flow_cm_s_first"] != ""]
        print(f"\n{inv}: {len(rs)} runs | O2 % {min(o2)}–{max(o2)} (n={len(o2)}) | "
              f"pressure atm {min(p) if p else '-'}–{max(p) if p else '-'} | flow cm/s {min(fl)}–{max(fl)} | "
              f"extinction noted in {sum(1 for r in rs if r['extinguished'])}")
        print("  materials:", dict(collections.Counter(r["material_family"] for r in rs).most_common()))
    others = [r["material_raw"] for r in runs if r["material_family"] == "other"]
    print("\nunclassified materials:", sorted(set(others))[:25])
