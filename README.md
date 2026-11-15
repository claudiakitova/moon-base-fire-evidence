# Moon Base Fire Evidence

**Has anything burned in space in a Moon Base atmosphere?**
Team Blue Flame · NASA Space Apps Challenge 2026 · *Flame in Freefall*

NASA plans Moon Base and pressurized-rover cabins at about **30% oxygen or more and 10.2 psi (0.694 atm) or less**, so crews can move into 100%-oxygen suits without long pre-breathing. More oxygen makes materials easier to ignite and faster to burn. We combined every test listed in the combustion tables of NASA's Physical Sciences Informatics (PSI) repository into one open, source-traced dataset and asked how much of it covers that atmosphere.

## Findings

| | Tests |
|---|---|
| Microgravity tests in PSI combustion "Experimental tables" (18 investigations) | **1,984** |
| Reach ≥30% oxygen around the flame, at any pressure | 290 (gas flames, fuel droplets, BRE solid emulator) |
| Inside the Moon Base box (≥30% O₂ **and** ≤0.694 atm) | **20**, all ACME CFI-G gas flames (butane/ethane, 33–39% O₂, 0.5 atm) |
| Just outside the box (0.70–0.71 atm, 10.3–10.5 psi) | 17 FLEX fuel droplets (methanol/heptane, 30–34% O₂) |
| **Solid materials (fabrics, plastics) above 22.7% O₂** | **0 in PSI** (NASA has run such tests; see finding 2) |
| ACME BRE (gas burner that emulates burning solids) at 34–40% O₂ | 17 test days; pressure not recorded in the table |

1. **In PSI, real materials stop at 22.7% oxygen.** Every solid sample with recorded oxygen (BASS, BASS-II, Saffire I–II; 261 tests) burned at or below normal air, most below it, because those experiments studied extinction.
2. **NASA has burned solids in Moon-like air, but that data isn't in PSI.** Saffire-VI (2021) burned cotton-fiberglass fabric at 31.0% O₂ and 54.1 kPa (7.8 psi), and PMMA at 28.8–30.3% O₂; Saffire-V burned cotton at 26.2% and 70.7 kPa ([NASA paper ICES-2024-365, Table 1](https://ntrs.nasa.gov/citations/20240002981)). SoFIE on the ISS was [built to test solids in these atmospheres](https://ntrs.nasa.gov/citations/20200000361) too. PSI holds Saffire I–III only, so the most Moon-relevant material tests are missing from the archive this challenge is built on. The dashboard shows the Saffire-V/VI points as hollow reference marks; they are not counted.
3. **Within PSI, the closest thing to Moon Base evidence is ACME BRE.** Its gas burner emulates burning solids. Its PSI record says the planned atmospheres included NASA's 10.2 psia / 26.5% and 8.2 psia / 34% O₂. It also reports that in elevated oxygen the flames kept burning with no airflow, while at 21% they self-extinguished. Cutting ventilation is a standard step in fighting a spacecraft fire. The run table records oxygen (up to 40%) but not pressure.
4. **PSI's high-oxygen evidence is not for habitat materials.** It comes from gas flames, droplets and the BRE emulator.
5. **Earth results can't simply be carried over to orbit.** Saffire-II (PSI-99) is PSI's only sample-by-sample comparison of Earth (1 g) and orbit. 5 of 9 samples burned farther on Earth and none burned farther in orbit; thin silicone burned completely on Earth and not at all in orbit. At these conditions (about 22% O₂, 20 cm/s) the Earth test was the harsher one, but the gap is large and depends on the material. The dashboard's "Earth vs. orbit" section shows all 9 samples. This is one set of conditions, not the general rule: BASS-II's PSI record hypothesizes that materials in microgravity with adequate ventilation "burn as well if not better" than on Earth, so NASA's upward-burning Earth test "may not be conservative for flammability in space."
6. **No partial-gravity data is in PSI yet.** Microgravity and 1 g can bracket the Moon's 1/6 g. ACME E-FIELD imitated partial gravity with an electric field. LUCI and FM2 data are expected later.

## Ranking: which investigations matter most
Each investigation gets a score out of 100 for two habitats: **Moon Base & rover** (≥30% O₂, ≤10.2 psi) and **Spacecraft & ISS** (about 21% O₂, 1 atm). The score has four parts:

| Part | Points | How it is set |
|---|---|---|
| What burned | 0–35 | Habitat solids 35, solid emulator 28, smoke from spacecraft materials 25, droplets 15, gas flames 10, dust 8. Ground studies get 70% of the material score of the data they analyze. |
| Fire-safety role | 0–25 | 25 for prevention, detection or suppression (the brief's three roles); 8 for basic flame science. |
| Atmosphere match | 0–25 | Computed from the PSI tables: tests inside or near the habitat's oxygen and pressure. Tables with no oxygen column score 0 for the Moon; for spacecraft they score 12 when the tests ran in Glovebox or Cygnus air, which is assumed to be about 21% at 1 atm. |
| Amount of data | 0–15 | Test rows in PSI tables (0–8) plus publications listed in PSI (0–7). |

The weights are our judgment. `ranking.csv` lists every component, so anyone can re-weight. Top results:
- **Moon Base:** BRE (80); BASS-II, BASS and FLEX (73 each); Saffire-I, II and III (65 each).
- **Spacecraft:** BASS (98), BASS-II (96), Saffire-I and Saffire-II (90 each), BRE (83).
- **Mars:** the brief defines no Mars habitat atmosphere, so the Moon ranking is the closest match.

## Dataset (`data/derived/`)

| File | Rows | What it is |
|---|---|---|
| `runs_all.csv` | 1,984 | One row per test from each investigation's official PSI "Experimental table" (BASS/BASS-II from the richer as-run matrices). Common columns: investigation, run id, fuel, fuel phase, O₂ %, pressure (atm), flow (cm/s), diluent, outcome, details, **source file + row**. |
| `runs_bass.csv` | 250 | BASS + BASS-II solid burns with material family, thickness, O₂ start/end, pressure, airflow sequence, extinction flag, final CO/CO₂ and the crew's observation text. |
| `investigations.csv` | 24 | All PSI combustion investigations: DOI, PSI page, hardware, dates, PI, objectives, Earth benefits, publication counts, PSI file inventory (files, GB, spreadsheets, video). |
| `publications.csv` | 352 | Publications listed on each PSI investigation page; 72 matched by exact title to a NASA Technical Reports Server (NTRS) record. |
| `investigation_profiles.json` | 24 | Per investigation: fire-safety role, summary, fuel and sample form, sensors, fire-safety relevance, Earth applications, conditions computed from the tables (oxygen, pressure, airflow ranges; what varied and what stayed fixed) and both rankings with reasons. |
| `ranking.csv` | 48 | Score components per investigation and habitat. |

The text notes (summary, fuel form, sensors, fire-safety relevance, Earth applications) are in `data/curated/investigation_notes.json`. Each note names the PSI record fields it comes from.

### Rules we followed
- **Copy, don't estimate.** Values are copied or unit-converted only (mmHg→atm ÷760, bar→atm ×0.986923, mole fraction→%). Missing stays empty.
- **Every row is traceable** to a PSI file and row (`source_file`, `source_row`).
- **Interpretations are flagged in the data, not hidden:**
  - ACME BRE cells reading `3400%` / `2100%` are read as 34% / 21% (spreadsheet percent-format slip); the row carries a `FLAG:` note.
  - A FLEX pressure of `0` mmHg (test 114) is treated as missing.
  - Text such as `LOW O2` is not parsed as a number.
  - BASS-II/BASS rows that name only a shape ("2 cm sphere") are labeled *PMMA (likely)*.
  - "Extinguished" in `runs_bass.csv` comes from keywords in crew notes, so it is a lower bound.
- **Inverse flames** (ACME CFI-G, Flame Design) are marked: their oxygen value is the burner stream, not the cabin atmosphere, so they are excluded from Moon Base counts.
- **Airflow** in BASS/BASS-II is the "Air display" value, read as cm/s (the BASS camera notes pair those values with cm/s).
- **Saffire tables** also contain footnote rows and pre-test flow-visualization recordings. These are not burns, so they are not counted; each footnote is attached to the rows that cite it (`details`).
- **FLEX-2** (PSI-68): its PSI table lists a test envelope per fuel (17–30% O₂, 0.5–3.0 atm), not individual runs. It appears as an envelope in the profiles and is not counted in the 1,984 tests.
- Where a PSI record's text and its table disagree (fuel names for Flame Design and CFI-G, the dust name for DAFT), the profile gives both.

### Sources
- NASA Physical Sciences Informatics: https://psi.nasa.gov/ (investigation records via the public search endpoint; files via the same endpoints the PSI web page uses). Each investigation's DOI (DataCite prefix 10.60555) is in `investigations.csv`; please cite PSI investigations by DOI.
- NASA Technical Reports Server API: https://ntrs.nasa.gov/api/citations/search
- Challenge brief and resources: https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/

## Dashboard (`docs/`)
A single static page (no server, no libraries). Open `docs/index.html` (also served by GitHub Pages). It has:
- the oxygen-vs-pressure chart with the Moon Base box
- the findings
- the ranking for each habitat, with a click-through breakdown of every score
- profiles of all 24 investigations, filterable by role and searchable
- a side-by-side comparison of two or three investigations
- a filterable table of all tests, which downloads as CSV
- Earth applications
- method, and links to download the full dataset

## How we used SI
The data-processing code, the dashboard code and the investigation notes (`data/curated/investigation_notes.json`) were written with **Claude (Anthropic)**, an SI tool, working from NASA PSI records and tables. The team chose the questions, scope and framing, and checked outputs against the sources. Each note names its PSI source fields, and every test row names its PSI file and row. The dataset files carry the same statement (`_generated_with` in the JSON files; this section for the CSVs).

## Reproduce
```
python code/psi_investigations.py        # PSI investigation records -> data/psi_combustion_investigations.json
python code/psi_files.py --list          # PSI file inventory -> data/psi_files/manifest.csv
python code/psi_get_experiment_tables.py  # official Experimental tables
python code/psi_get_tables.py            # run tables, logs, readmes (~470 MB)
python code/ntrs_harvest.py --no-pdfs    # NTRS records linked to each investigation
python code/build_runs_bass.py
python code/build_runs_all.py
python code/build_investigations.py
python code/build_insights.py            # profiles + ranking
python code/build_site.py
```
Python 3.11, `requests`, `openpyxl`.

## Weekly updates
From February 1, 2027 (after Space Apps judging), a GitHub Actions workflow (`.github/workflows/update-data.yml`) re-downloads the PSI records and tables every Monday, rebuilds the dataset, ranking and dashboard, and commits any changes. If PSI adds an investigation that has no written profile yet, it opens an issue instead of publishing a blank one.

## Limits
- **PSI only.** Every count here is about what PSI's combustion tables hold, not everything NASA has flown. Saffire IV–VI and SoFIE are not in PSI yet.
- PSI tables differ in what they record; many lack pressure or flow. We report what each table gives.
- Investigation-level tables (FLEX-2, CLD Flame, E-FIELD, s-Flame, SLICE) list conditions per test day or as ranges, not per run.
- This is a map of where evidence exists, not a flammability model. It does not certify materials or predict fires.

## License
Code: MIT. Derived tables: CC0. The underlying data is NASA's; PSI asks users to cite each investigation by its persistent identifier, so please cite the DOIs in `investigations.csv`.
