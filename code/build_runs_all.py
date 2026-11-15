"""All PSI 'Experimental table' CSVs (+ the richer BASS/BASS-II build) -> one table: data/derived/runs_all.csv

One row per test/run as PSI lists it. Common columns; values are copied or unit-converted, never invented:
  o2_pct          oxygen mole fraction x100 (or the PSI '% O2' value). If a row lists several (BRE '21; 26.5; 40'),
                  o2_pct = lowest, o2_pct_max = highest.
  pressure_atm    mmHg/760, bar*0.986923; empty when the table has no pressure.
  flow_cm_s       air/oxidizer flow if the table gives one.
  fuel_phase      solid / liquid droplet / gas / gas burner emulating solids (BRE) / dust (DAFT)
  outcome         the table's own outcome text (e.g. FLEX 'Test end', CFI-G 'Self-ext or flow term', Saffire burn length)
  source_file + source_row  -> exact place in the PSI CSV
"""
import csv, io, re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SRC = DATA / "psi_files"
OUT = DATA / "derived"
COLS = ["investigation", "psi", "run_id", "date", "fuel", "fuel_phase", "o2_pct", "o2_pct_max", "pressure_atm",
        "flow_cm_s", "diluent", "outcome", "details", "gravity", "source_file", "source_row"]
NUM = re.compile(r"-?\d*\.?\d+")


def read(psi, name_part):
    f = next((SRC / psi / "Experimental table").glob(f"*{name_part}*"))
    raw = f.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc); break
        except UnicodeDecodeError:
            pass
    rows = list(csv.reader(io.StringIO(txt)))
    hdr = [h.strip() for h in rows[0]]
    out = []
    for i, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        out.append((i, {h: (r[k].strip() if k < len(r) else "") for k, h in enumerate(hdr)}))
    return f.name, out


def col(d, *keys):
    for k in d:
        if any(key.lower() in k.lower() for key in keys):
            return d[k]
    return ""


def nums(s):
    """Numbers in a cell, ignoring digits that belong to words/formulas (e.g. 'LOW O2', 'C2H4')."""
    if not s:
        return []
    s = re.sub(r"[A-Za-z]+\d*[A-Za-z\d]*", " ", str(s).replace(",", "."))
    return [float(x) for x in NUM.findall(s)]


FLAGS = {}   # (source_file, row) -> note about a value we had to interpret


def frac_to_pct(v, where=None):
    n = nums(v)
    if not n:
        return "", ""
    if where and any(x > 100 for x in n) and "%" in str(v):
        FLAGS[where] = f"source shows '{v.strip()}'; read as {', '.join(f'{x/100:g}' for x in n)}% (spreadsheet percent-format slip)"
        n = [x / 100 if x > 100 else x for x in n]
    n = [x * 100 if x <= 1 else x for x in n]
    return round(min(n), 2), (round(max(n), 2) if max(n) != min(n) else "")


def row(**kw):
    r = {c: "" for c in COLS}; r.update(kw); r["gravity"] = r["gravity"] or "microgravity (ISS)"
    return r


def flex():
    fn, rows = read("PSI-69", "FLEX")
    out = []
    for i, d in rows:
        p = nums(col(d, "pressure"))
        co2, he = col(d, "CO"), col(d, "He initial")
        dil = "; ".join(x for x in (f"CO2 {co2}" if nums(co2) and nums(co2)[0] > 0 else "",
                                    f"He {he}" if nums(he) and nums(he)[0] > 0 else "") if x)
        o2, _ = frac_to_pct(col(d, "O initial"))
        out.append(row(investigation="FLEX", psi="PSI-69", run_id=f"FLEX-{col(d, 'FLEX Test #')}", date=col(d, "Test Date"),
                       fuel=col(d, "Fuel"), fuel_phase="liquid droplet", o2_pct=o2,
                       pressure_atm=round(p[0] / 760, 3) if p and p[0] > 0 else "",   # 0 mmHg in source = missing
                       diluent=dil, outcome=col(d, "Test end"),
                       details=f"d0={col(d, 'Droplet initial')} mm; extinction d={col(d, 'extinction diame')} mm; "
                               f"burn rate={col(d, 'Burning rate')}; burn time={col(d, 'Burn time')} s",
                       source_file=fn, source_row=i))
    return out


def cfi():
    fn, rows = read("PSI-39", "CFI")
    out = []
    for i, d in rows:
        p = nums(col(d, "Pressure")); o2, _ = frac_to_pct(col(d, "Oxygen")); he = nums(col(d, "Helium"))
        out.append(row(investigation="CFI", psi="PSI-39", run_id=f"CFI-{col(d, 'Flex Number')}", date=col(d, "Test Date"),
                       fuel=col(d, "Fuel"), fuel_phase="liquid droplet", o2_pct=o2, pressure_atm=p[0] if p else "",
                       diluent=f"He {he[0]}" if he and he[0] > 0 else "", details=f"fiber={col(d, 'Fiber')}",
                       source_file=fn, source_row=i))
    return out


def cfig():
    out = []
    for part, kind in (("Normal", "normal"), ("Inverse", "inverse")):
        fn, rows = read("PSI-159", part)
        for i, d in rows:
            o2 = col(d, "XO2 before") if kind == "normal" else col(d, "XO2")
            o2p, _ = frac_to_pct(o2); p = nums(col(d, "approx p"))
            out.append(row(investigation="ACME CFI-G", psi="PSI-159", run_id=f"CFI-G-{col(d, 'Test')}".replace(" ", ""),
                           date=f"day {col(d, 'Day')}", fuel=col(d, "Fuel"), fuel_phase=f"gas ({kind} flame)", o2_pct=o2p,
                           pressure_atm=round(p[0] * 0.986923, 3) if p else "",
                           outcome="; ".join(x for x in (f"hot ignition={col(d, 'Hot ignition')}" if col(d, 'Hot ignition') else "",
                                                         f"end={col(d, 'Self')}" if col(d, 'Self') else "",
                                                         f"burn {col(d, 'burn time')} s" if col(d, 'burn time') else "") if x),
                           details=f"cool flame={col(d, 'Cool flame')}; {col(d, 'Comments')}".strip("; "),
                           source_file=fn, source_row=i))
    return out


def flame_design():
    out = []
    for part, kind in (("Normal", "normal"), ("Inverse", "inverse")):
        fn, rows = read("PSI-10", part)
        for i, d in rows:
            o2 = col(d, "XO2 (init)") if kind == "normal" else col(d, "XO2")
            o2p, _ = frac_to_pct(o2); p = nums(col(d, "pmean"))
            out.append(row(investigation="ACME Flame Design", psi="PSI-10", run_id=f"FD-{col(d, 'Test')}", date=f"day {col(d, 'Day')}",
                           fuel=col(d, "Fuel") or "C2H4", fuel_phase=f"gas ({kind} flame)", o2_pct=o2p,
                           pressure_atm=p[0] if p else "", details=f"Tad={col(d, 'Tad')} K; Zst={col(d, 'Zst')}",
                           source_file=fn, source_row=i))
    return out


def bre():
    fn, rows = read("PSI-20", "BRE")
    out = []
    for i, d in rows:
        lo, hi = frac_to_pct(col(d, "Oxygen Conc"), where=(fn, i))
        flag = FLAGS.get((fn, i), "")
        out.append(row(investigation="ACME BRE", psi="PSI-20", run_id=f"BRE-{col(d, 'Year')}-{col(d, 'Month')}-{col(d, 'Date')}",
                       date=f"{col(d, 'Year')}-{col(d, 'Month')}-{col(d, 'Date')}", fuel=col(d, "Fuel Bottle"),
                       fuel_phase="gas burner emulating burning solids", o2_pct=lo, o2_pct_max=hi,
                       outcome=f"flames ignited={col(d, 'Flames Ignited')}",
                       details="; ".join(x for x in (f"FLAG: {flag}" if flag else "", f"burner {col(d, 'Burner Size')} mm", col(d, "Notes")) if x),
                       source_file=fn, source_row=i))
    return out


def acme_day(psi, part, name):
    fn, rows = read(psi, part)
    out = []
    for i, d in rows:
        atm = col(d, "Atmosphere")
        o2 = re.search(r"(\d+(?:\.\d+)?)\s*%\s*O2", atm)
        out.append(row(investigation=name, psi=psi, run_id=f"{name.split()[-1]}-{col(d, 'Test Day')}", date=col(d, "Test Day"),
                       fuel=col(d, "Fuel Bottle"), fuel_phase="gas", o2_pct=float(o2.group(1)) if o2 else "",
                       outcome=f"flames ignited={col(d, 'Flames ignited')}",
                       details="; ".join(x for x in (col(d, "Test Type"), f"fuel conc {col(d, 'Fuel conc')}" if col(d, 'Fuel conc') else "",
                                                     f"mesh {col(d, 'Mesh')}" if col(d, 'Mesh') else "", atm, col(d, "Notes")) if x),
                       source_file=fn, source_row=i))
    return out


def spice():
    fn, rows = read("PSI-107", "Spice")
    return [row(investigation="SPICE", psi="PSI-107", run_id=f"SPICE-{i}", date=f"GMT {col(d, 'GMT date')}",
                fuel=col(d, "Fuel"), fuel_phase="gas (coflow jet)", flow_cm_s=(nums(col(d, "Air Rate")) or [""])[0],
                details=f"nozzle {col(d, 'Nozzle')} mm; fuel {col(d, 'Fuel Rate (mg/s)')} mg/s", source_file=fn, source_row=i)
            for i, d in rows]


def slice_():
    fn, rows = read("PSI-106", "Slice")
    return [row(investigation="SLICE", psi="PSI-106", run_id=f"SLICE-{i}", date=col(d, "Test Date"), fuel=col(d, "Fuel Type"),
                fuel_phase="gas (coflow jet)", source_file=fn, source_row=i) for i, d in rows]


def same():
    out = []
    fn, rows = read("PSI-102", "SAME")
    for i, d in rows:
        out.append(row(investigation="SAME", psi="PSI-102", run_id=f"SAME-{col(d, 'Sample #')}", fuel=col(d, "Sample Material"),
                       fuel_phase="solid (heated, smoke)", flow_cm_s=(nums(col(d, "Air Flow")) or [""])[0],
                       details=f"weight loss {col(d, 'Weight loss')} mg/min; aging {col(d, 'Aging')} min", source_file=fn, source_row=i))
    fn, rows = read("PSI-101", "SAME-R")
    for i, d in rows:
        out.append(row(investigation="SAME-R", psi="PSI-101", run_id=f"SAME-R-{col(d, 'SAME Test #')}", date=col(d, "Date"),
                       fuel=col(d, "Sample Type"), fuel_phase="solid (heated, smoke)", flow_cm_s=(nums(col(d, "Inlet velocity")) or [""])[0],
                       details=f"{col(d, 'Description')}; duration {col(d, 'Duration')} s", source_file=fn, source_row=i))
    return out


def saffire():
    out = []
    for psi, part, name in (("PSI-98", "SAFFIRE-1", "Saffire-I"), ("PSI-99", "SAFFIRE-2", "Saffire-II"), ("PSI-100", "SAFFIRE-3", "Saffire-III")):
        fn, rows = read(psi, part)
        # The tables also hold footnote rows ("Note 1 ...") and pre-test flow-visualization recordings.
        # Neither is a burn: footnotes are attached to the rows that cite them; flow recordings are skipped.
        notes = {}
        for i, d in rows:
            m = re.match(r"\s*Note\s*(\d+)\s*(.*)", col(d, "Sample Number"), re.S)
            if m:
                notes[m.group(1)] = m.group(2).strip()
        tests = [(i, d) for i, d in rows if not re.match(r"\s*Note\s*\d", col(d, "Sample Number"))
                 and not col(d, "Material").lower().startswith("pre-test flow")]
        for i, d in tests:
            lo, hi = frac_to_pct(col(d, "Percent O2"))
            outc = "; ".join(x for x in (f"µg burn length={col(d, 'g Burn Length')}" if col(d, 'g Burn Length') else "",
                                         f"µg spread={col(d, 'g Spread Length')}" if col(d, 'g Spread Length') else "",
                                         f"1g burn length={col(d, '1-g Burn')}" if col(d, '1-g Burn') else "",
                                         f"1g spread rate={col(d, '1-g Spread')}" if col(d, '1-g Spread') else "",
                                         f"burn time={col(d, 'Burn Time')}" if col(d, 'Burn Time') else "") if x)
            cited = sorted(set(re.findall(r"(?i)note\s*(\d+)", " ".join(str(v) for v in d.values()) + " " + " ".join(d.keys()))))
            det = "; ".join(x for x in [f"thickness {col(d, 'Thickness')}", col(d, "Direction")] +
                            [f"Note {n}: {notes[n]}" for n in cited if n in notes] if x)
            if not col(d, "Material"):
                det += "; material cell blank in the PSI table"
            out.append(row(investigation=name, psi=psi, run_id=f"{name}-{col(d, 'Sample Number')}", fuel=col(d, "Material"),
                           fuel_phase="solid", o2_pct=lo, o2_pct_max=hi, flow_cm_s=(nums(col(d, "Air Flow")) or [""])[0],
                           outcome=outc, details=det,
                           gravity="microgravity (Cygnus, after ISS departure)", source_file=fn, source_row=i))
    return out


def daft():
    fn, rows = read("PSI-47", "DAFT")
    return [row(investigation="DAFT", psi="PSI-47", run_id=f"DAFT-{col(d, 'Session')}", date=col(d, "Actual Day"),
                fuel=col(d, "Sample Material"), fuel_phase="dust (no combustion)",
                details=f"{col(d, 'Hardware')}; {col(d, 'Sampled Location')}", source_file=fn, source_row=i) for i, d in rows]


def bass_rich():
    """Reuse the richer BASS/BASS-II build (O2, pressure, flow, CO) from runs_bass.csv."""
    out = []
    for r in csv.DictReader(open(OUT / "runs_bass.csv", encoding="utf-8-sig")):
        out.append(row(investigation=r["investigation"], psi=r["psi"], run_id=r["run_id"], date=r["date"], fuel=r["material_raw"],
                       fuel_phase="solid", o2_pct=r["o2_pct_initial"], pressure_atm=r["pressure_atm"], flow_cm_s=r["flow_cm_s_first"],
                       outcome="extinction noted" if r["extinguished"] else "",
                       details="; ".join(x for x in (f"family={r['material_family']}",
                                                     f"flow sequence={r['flow_raw']}" if r["flow_raw"] else "",
                                                     f"final CO={r['co_ppm_final']} ppm" if r["co_ppm_final"] else "",
                                                     r["observations"]) if x)[:400],
                       source_file=r["source_file"], source_row=r["source_sheet"]))
    return out


if __name__ == "__main__":
    runs = (bass_rich() + saffire() + flex() + cfi() + cfig() + flame_design() + bre()
            + acme_day("PSI-21", "CLD", "ACME CLD Flame") + acme_day("PSI-22", "E-FIELD", "ACME E-FIELD Flames")
            + acme_day("PSI-23", "s-Flame", "ACME s-Flame") + spice() + slice_() + same() + daft())
    with open(OUT / "runs_all.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(runs)
    import collections
    print(f"rows: {len(runs)} -> {OUT / 'runs_all.csv'}\n")
    by = collections.defaultdict(list)
    for r in runs:
        by[r["investigation"]].append(r)
    print(f"{'investigation':22} {'rows':>5}  {'O2 % range':>14}  {'p atm range':>14}  phase")
    for k, rs in by.items():
        o2 = [float(r["o2_pct"]) for r in rs if r["o2_pct"] not in ("", None)] + [float(r["o2_pct_max"]) for r in rs if r["o2_pct_max"] not in ("", None)]
        p = [float(r["pressure_atm"]) for r in rs if r["pressure_atm"] not in ("", None)]
        print(f"{k:22} {len(rs):5}  {(f'{min(o2):.1f}–{max(o2):.1f}' if o2 else '—'):>14}  {(f'{min(p):.2f}–{max(p):.2f}' if p else '—'):>14}  {rs[0]['fuel_phase']}")
