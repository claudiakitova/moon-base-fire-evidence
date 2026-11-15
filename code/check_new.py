"""Print PSI investigations that have no written profile in data/curated/investigation_notes.json (empty if none)."""
import csv, json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
notes = json.load(open(BASE / "data" / "curated" / "investigation_notes.json", encoding="utf-8"))
inv = list(csv.DictReader(open(BASE / "data" / "derived" / "investigations.csv", encoding="utf-8-sig")))
missing = [f'{r["psi"]} ({r["acronym"] or r["title"][:50]})' for r in inv if r["psi"] not in notes]
print(", ".join(missing))
