"""Pack derived data into docs/data.js for the static dashboard (no server needed) and copy the
dataset files into docs/data/ so the page can offer them for download. docs/ is what GitHub Pages serves."""
import csv, json, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
D = BASE / "data" / "derived"
SITE = BASE / "docs"
(SITE / "data").mkdir(parents=True, exist_ok=True)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def phase_group(p):
    p = p.lower()
    if p.startswith("solid") and "smoke" not in p:
        return "solid"
    if "droplet" in p:
        return "droplet"
    if "emulating" in p:
        return "emulator"
    if p.startswith("gas"):
        return "gas"
    return "other"


runs = []
for r in csv.DictReader(open(D / "runs_all.csv", encoding="utf-8-sig")):
    runs.append({
        "inv": r["investigation"], "psi": r["psi"], "id": r["run_id"], "date": r["date"], "fuel": r["fuel"],
        "phase": r["fuel_phase"], "grp": phase_group(r["fuel_phase"]), "inverse": "inverse" in r["fuel_phase"],
        "o2": num(r["o2_pct"]), "o2max": num(r["o2_pct_max"]), "p": num(r["pressure_atm"]), "flow": num(r["flow_cm_s"]),
        "dil": r["diluent"], "out": r["outcome"], "det": r["details"], "g": r["gravity"],
        "src": r["source_file"], "row": r["source_row"],
    })
prof = json.load(open(D / "investigation_profiles.json", encoding="utf-8"))
profiles = prof["profiles"]
inv ={r["psi"]: r for r in csv.DictReader(open(D / "investigations.csv", encoding="utf-8-sig"))}
for p in profiles:
    p["objectives"] = inv[p["psi"]]["objectives"]
    p["earth_benefits_psi"] = inv[p["psi"]]["earth_benefits"]

# Earth (1 g) vs orbit, sample by sample: PSI's only paired table is Saffire-II (PSI-99).
# Values are copied from runs_all.csv; the verdict column is our reading of them (SI-written, team-checked).
VERDICT = {
    "Saffire-II-2-1": "Burned on Earth, not in orbit",
    "Saffire-II-2-2": "Burned on Earth, not in orbit",
    "Saffire-II-2-3": "Did not burn in either",
    "Saffire-II-2-4": "Burned on Earth, not in orbit",
    "Saffire-II-2-5": "Burned the full sample in both (steady in orbit, accelerating on Earth)",
    "Saffire-II-2-6": "Burned the full sample in both (steady in orbit, accelerating on Earth)",
    "Saffire-II-2-7": "Nomex did not ignite in either; the PMMA part burned away in orbit",
    "Saffire-II-2-8": "Burned farther on Earth (complete vs ~10 cm in orbit)",
    "Saffire-II-2-9": "Burned farther on Earth (complete vs ~10 cm in orbit)",
}


def field(outcome, key):
    for part in outcome.split("; "):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return ""


gf = []
for r in runs:
    if r["id"] in VERDICT:
        gf.append({"id": r["id"], "material": r["fuel"] or "(blank in PSI table)",
                   "thickness": r["det"].split(";")[0].replace("thickness ", ""),
                   "flow": f"{r['flow']:g} cm/s" if r["flow"] is not None else "",
                   "direction": (r["det"].split("; ") + [""])[1],
                   "g1": f"{field(r['out'], '1g burn length')}; spread {field(r['out'], '1g spread rate')}",
                   "ug": f"{field(r['out'], 'µg burn length')}; spread {field(r['out'], 'µg spread')}",
                   "verdict": VERDICT[r["id"]], "row": r["row"], "src": r["src"]})
assert len(gf) == len(VERDICT), "Saffire-II rows changed; re-check the verdicts"

(SITE / "data.js").write_text(
    "window.FIF_DATA = " + json.dumps({"runs": runs, "profiles": profiles, "gf": gf, "generated_with": prof["_generated_with"]},
                                      ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
for name in ("runs_all.csv", "runs_bass.csv", "investigations.csv", "publications.csv", "ranking.csv",
             "investigation_profiles.json"):
    shutil.copy2(D / name, SITE / "data" / name)
print(f"docs/data.js: {len(runs)} runs, {len(profiles)} profiles, {(SITE / 'data.js').stat().st_size/1024:.0f} KB")
