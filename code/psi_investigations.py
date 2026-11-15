"""Fetch NASA PSI investigation records (public search endpoint) and keep the combustion ones.

Output: data/psi_combustion_investigations.json  (list of PSI investigation records)
"""
import json, sys
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
URL = "https://psi.nasa.gov/geode-py/ws/repo/search"


def records(obj):
    """Find the list of investigation records in the search response, whatever it is wrapped in."""
    if isinstance(obj, list):
        return obj if obj and isinstance(obj[0], dict) and "Accession" in obj[0] else [x for o in obj for x in records(o)]
    if isinstance(obj, dict):
        if "Accession" in obj:
            return [obj]
        return [x for v in obj.values() if isinstance(v, (list, dict)) for x in records(v)]
    return []


r = requests.get(URL, params={"data_source": "psi", "data_type": "investigation", "size": 300}, timeout=60)
r.raise_for_status()
allrec = records(r.json())
comb = [x.get("_source", x) for x in allrec if "combustion" in str(x.get("Research Area", "")).lower()]
if not comb:
    sys.exit(f"No combustion records found among {len(allrec)}; the response format may have changed.")
out = DATA / "psi_combustion_investigations.json"
if "--check" in sys.argv:
    old = json.loads(out.read_text(encoding="utf-8-sig"))
    print("existing:", sorted(x["Accession"] for x in old) == sorted(x["Accession"] for x in comb), len(old), len(comb))
else:
    out.write_text(json.dumps(comb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(comb)} combustion investigations of {len(allrec)} PSI records -> {out}")
