"""Per-investigation profiles + transparent relevance ranking.

Inputs : data/derived/runs_all.csv, data/derived/investigations.csv, data/curated/investigation_notes.json
Output : data/derived/investigation_profiles.json, data/derived/ranking.csv

Ranking (0-100) per environment = material + role + atmosphere + evidence.
  material   (0-35): what burned. Real habitat solids 35, solid emulator (BRE) 28, smoke from spacecraft
                     materials 25, liquid droplets 15, gas flames 10, dust/no fire 8.
                     Ground studies of flight data get 70% of the material score of what they analyze.
  role       (0-25): brief's fire-safety roles. Prevention / detection / suppression 25; fundamentals 8.
  atmosphere (0-25): how close the tested atmospheres come to the environment (computed from runs_all.csv;
                     see atm_spacecraft / atm_moon). Ground studies 0.
  evidence   (0-15): run-level rows in PSI tables (0-8) + publications listed in PSI (0-7).
Every component is reported, so the rank can be checked and re-weighted.
"""
import csv, json, math
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
D = BASE / "data" / "derived"
notes = json.load(open(BASE / "data" / "curated" / "investigation_notes.json", encoding="utf-8"))
inv = {r["psi"]: r for r in csv.DictReader(open(D / "investigations.csv", encoding="utf-8-sig"))}
runs = defaultdict(list)
for r in csv.DictReader(open(D / "runs_all.csv", encoding="utf-8-sig")):
    runs[r["psi"]].append(r)

MOON_O2, MOON_P = 30.0, 10.2 / 14.696  # 0.694 atm


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def rng(vals):
    v = [x for x in vals if x is not None]
    return [min(v), max(v)] if v else None


def conditions(rs):
    amb = [r for r in rs if "inverse" not in r["fuel_phase"]]
    o2 = [f(r["o2_pct"]) for r in amb] + [f(r["o2_pct_max"]) for r in amb]
    p = [f(r["pressure_atm"]) for r in amb]
    fl = [f(r["flow_cm_s"]) for r in rs]
    fuels = sorted({r["fuel"].strip() for r in rs if r["fuel"].strip()})
    dil = sorted({r["diluent"].strip() for r in rs if r["diluent"].strip()})
    varied, fixed = [], []
    for name, vals in (("fuel", [r["fuel"] for r in rs]), ("oxygen", [r["o2_pct"] for r in rs]),
                       ("pressure", [r["pressure_atm"] for r in rs]), ("airflow", [r["flow_cm_s"] for r in rs]),
                       ("diluent", [r["diluent"] for r in rs])):
        s = {v.strip() for v in vals if v and v.strip()}
        if len(s) > 1:
            varied.append(name)
        elif len(s) == 1:
            fixed.append(f"{name} = {next(iter(s))}")
    return {"runs": len(rs), "runs_inverse": len(rs) - len(amb), "o2_pct": rng(o2), "pressure_atm": rng(p),
            "flow_cm_s": rng(fl), "fuels": fuels[:12], "fuels_total": len(fuels), "diluents": dil[:6],
            "varied": varied, "fixed": fixed}


def has_o2(rs):
    return any(f(r["o2_pct"]) is not None or f(r["o2_pct_max"]) is not None for r in rs)


# PSI-68 (FLEX-2): the PSI Experimental table lists a test envelope per fuel, not individual runs.
ENVELOPE = {"PSI-68": {
    "source": "PSI-68_Experimental table_Flex2.csv",
    "fuels": ["IsoOctane", "n-Octane", "Heptane", "Decane", "Ethanol", "Propanol 95% / Glycerol 5%",
              "Heptane 50% / IsoOctane 50%", "Propanol 80% / Glycerol 20%"],
    "o2_pct": [17, 30], "o2_levels": "17, 21, 25, 30%", "pressure_atm": [0.5, 3.0],
    "pressure_levels": "0.5, 1.0, 1.5, 2.0 or 3.0 atm", "flow_cm_s": [0.1, 5], "droplet_mm": "1.5-5",
    "diluents": ["O2/N2", "O2/He"],
    "moon": (12, "PSI test envelope lists 30% O2 and 0.5 atm among its options, but not which combinations were run."),
    "spacecraft": (15, "PSI test envelope includes 21% O2 and 1.0 atm; individual runs are not listed.")}}


def atm_moon(rs):
    amb = [r for r in rs if "inverse" not in r["fuel_phase"]]
    if not has_o2(amb):
        return 0, "Oxygen is not recorded in the PSI table."
    best, why = 0, "No tests at elevated oxygen in the PSI table."
    for r in amb:
        o2 = max([x for x in (f(r["o2_pct"]), f(r["o2_pct_max"])) if x is not None], default=None)
        p = f(r["pressure_atm"])
        if o2 is None:
            continue
        if o2 >= MOON_O2 and p is not None and p <= MOON_P + 1e-9:
            s, w = 25, "Has tests inside the Moon Base box (>=30% O2 and <=0.694 atm)."
        elif o2 >= MOON_O2 and (p is None or p <= MOON_P + 0.05):
            s, w = 18, "Has tests at >=30% O2 at or near Moon Base pressure (or pressure not recorded)."
        elif o2 >= MOON_O2:
            s, w = 14, "Has tests at >=30% O2, but only at higher pressure than the Moon Base."
        elif o2 >= 25:
            s, w = 8, "Highest oxygen tested is 25-30%."
        elif o2 > 23:
            s, w = 4, "Oxygen tested only slightly above air (23-25%)."
        else:
            s, w = 0, "All tests at or below normal air (21%)."
        if s > best:
            best, why = s, w
    return best, why


# Tests that ran in spacecraft air even though the table has no O2 column: Microgravity Science Glovebox
# fan-driven duct (challenge brief: SPICE, SLICE; PSI-102 record: SAME in the Glovebox) and the Cygnus module.
CABIN_AIR = {"PSI-100": "Cygnus cargo module air", "PSI-101": "Glovebox air", "PSI-102": "Glovebox air",
             "PSI-106": "Glovebox flow-duct air", "PSI-107": "Glovebox flow-duct air"}


def atm_spacecraft(rs):
    amb = [r for r in rs if "inverse" not in r["fuel_phase"]]
    if not has_o2(amb):
        where = CABIN_AIR.get(rs[0]["psi"])
        if where:
            return 12, f"Oxygen is not recorded in the PSI table; tests ran in {where} (assumed about 21%, 1 atm)."
        return 0, "Oxygen is not recorded in the PSI table."
    near = loose = 0
    for r in amb:
        o2, p = f(r["o2_pct"]), f(r["pressure_atm"])
        if o2 is None:
            continue
        if 19 <= o2 <= 23 and (p is None or 0.9 <= p <= 1.1):
            near += 1
        elif 15 <= o2 <= 25:
            loose += 1
    if not amb or near + loose == 0:
        return 0, "No tests near cabin air (21% O2, 1 atm) in the PSI table."
    if near:
        share = near / len(amb)
        s = 15 + round(10 * min(1, share * 2))
        return s, f"{near} of {len(amb)} tests near cabin air (19-23% O2, ~1 atm or pressure not recorded)."
    return 10, f"{loose} tests at 15-25% O2 but not near 1 atm cabin air."


MATERIAL = {"solid": 35, "emulator": 28, "smoke": 25, "droplet": 15, "gas": 10, "aerosol": 8}


def evidence(psi, n_runs):
    pubs = int(inv[psi].get("publications_listed_in_psi") or 0)
    r = 8 if n_runs >= 100 else 6 if n_runs >= 30 else 4 if n_runs >= 10 else 2 if n_runs else 0
    p = 7 if pubs >= 20 else 5 if pubs >= 10 else 3 if pubs >= 3 else 1 if pubs else 0
    return r + p, f"{n_runs} test rows in PSI tables, {pubs} publications listed in PSI."


profiles, rank_rows = [], []
for psi, meta in inv.items():
    n = notes.get(psi, {})
    rs = runs.get(psi, [])
    cond = conditions(rs) if rs else None
    ground = bool(n.get("ground"))
    mat = MATERIAL.get(n.get("material"), 10)
    mat_why = f"Burned/used: {n.get('material', 'unknown')}."
    if ground:
        mat = round(mat * 0.7)
        mat_why = f"Ground study of {n.get('parent')} data ({n.get('material')}); 70% of flight material score."
    roles = n.get("roles", ["fundamentals"])
    role = 25 if set(roles) & {"prevention", "detection", "suppression"} else 8
    role_why = "Fire-safety role: " + ", ".join(roles) + "."
    ev, ev_why = evidence(psi, len(rs))
    scores = {}
    env_ = ENVELOPE.get(psi)
    if env_:
        cond = {"runs": 0, "envelope": True, "source": env_["source"], "o2_pct": env_["o2_pct"],
                "o2_levels": env_["o2_levels"], "pressure_atm": env_["pressure_atm"],
                "pressure_levels": env_["pressure_levels"], "flow_cm_s": env_["flow_cm_s"],
                "droplet_mm": env_["droplet_mm"], "fuels": env_["fuels"], "fuels_total": len(env_["fuels"]),
                "diluents": env_["diluents"], "varied": ["fuel", "oxygen", "pressure", "diluent", "droplet size"],
                "fixed": ["ambient temperature = 25 C"]}
    for env, fn in (("spacecraft", atm_spacecraft), ("moon", atm_moon)):
        if env_:
            a, a_why = env_[env]
        elif ground:
            a, a_why = 0, "Ground study: no flight atmosphere of its own."
        elif not rs:
            a, a_why = 0, "No run-level table in PSI, so atmosphere coverage cannot be computed."
        else:
            a, a_why = fn(rs)
        # BRE: the PSI record states NASA exploration atmospheres were planned (10.2 psia/26.5%, 8.2 psia/34%);
        # the table has 34-40% O2 but no pressure. We keep the table-based score and add the note.
        total = mat + role + a + ev
        scores[env] = {"total": total, "material": mat, "role": role, "atmosphere": a, "evidence": ev,
                       "why": [mat_why, role_why, a_why, ev_why]}
        rank_rows.append({"environment": env, "psi": psi, "acronym": meta["acronym"] or meta["title"][:40],
                          "total": total, "material": mat, "role": role, "atmosphere": a, "evidence": ev,
                          "why_atmosphere": a_why})
    profiles.append({"psi": psi, "acronym": meta["acronym"], "title": meta["title"], "doi": meta["doi"],
                     "psi_page": meta["psi_page"], "project_type": meta["project_type"], "hardware": meta["hardware"],
                     "start": meta["start"], "end": meta["end"], "pi": meta["pi"],
                     "publications": int(meta.get("publications_listed_in_psi") or 0),
                     "ntrs": int(meta.get("ntrs_reports_linked") or 0),
                     "psi_files": meta["psi_files"], "psi_total_gb": meta["psi_total_gb"],
                     "conditions": cond, "notes": {k: v for k, v in n.items()}, "scores": scores})

for env in ("spacecraft", "moon"):
    ordered = sorted([p for p in profiles], key=lambda p: -p["scores"][env]["total"])
    for i, p in enumerate(ordered, 1):
        p["scores"][env]["rank"] = i

(D / "investigation_profiles.json").write_text(json.dumps({
    "_method": __doc__, "_generated_with": notes["_generated_with"], "profiles": profiles}, ensure_ascii=False, indent=1),
    encoding="utf-8")
rank_rows.sort(key=lambda r: (r["environment"], -r["total"]))
with open(D / "ranking.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rank_rows[0]))
    w.writeheader()
    w.writerows(rank_rows)

for env in ("moon", "spacecraft"):
    print(f"\n== {env}")
    for r in [x for x in rank_rows if x["environment"] == env]:
        print(f"{r['total']:>3}  {r['psi']:<8} {r['acronym'][:28]:<28} m{r['material']} r{r['role']} a{r['atmosphere']} e{r['evidence']}  {r['why_atmosphere']}")
for p in profiles:
    c = p["conditions"]
    if c:
        print(p["psi"], c["runs"], "O2", c["o2_pct"], "P", c["pressure_atm"], "flow", c["flow_cm_s"], "varied", c["varied"], "| fuels", c["fuels"][:5])
