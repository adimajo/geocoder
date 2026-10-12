"""Generate a deterministic set of (code_postal, commune, adresse) queries from the raw BAN csv of dept 01.

Usage: python benchmarks/make_cases.py > benchmarks/cases.json
"""
import csv
import json
import random
import sys

RAW = sys.argv[1] if len(sys.argv) > 1 else "geocoder/geocoding/raw/adresses-01.csv"
random.seed(42)


def typo(text):
    if len(text) < 6:
        return text
    i = random.randrange(1, len(text) - 1)
    return text[:i] + text[i + 1:]


with open(RAW, encoding="utf-8") as f:
    rows = list(csv.reader(f, delimiter=";"))[1:]
rows = random.sample(rows, 400)

cases = []
for r in rows:
    numero, rep, voie, cp, commune = r[2], r[3], r[4], r[5], r[7]
    adresse = f"{numero}{rep} {voie}".strip()
    kind = random.choice(["exact", "typo_voie", "typo_commune", "no_commune", "no_cp", "no_numero", "voie_only"])
    c = {"code_postal": cp, "commune": commune, "adresse": adresse, "truth": [float(r[12]), float(r[13])]}
    if kind == "typo_voie":
        c["adresse"] = f"{numero} {typo(voie)}"
    elif kind == "typo_commune":
        c["commune"] = typo(commune)
    elif kind == "no_commune":
        c["commune"] = None
    elif kind == "no_cp":
        c["code_postal"] = None
    elif kind == "no_numero":
        c["adresse"] = voie
    elif kind == "voie_only":
        c["code_postal"], c["commune"] = None, None
    c["kind"] = kind
    cases.append(c)

points = [(float(r[12]) + random.uniform(-1e-4, 1e-4), float(r[13]) + random.uniform(-1e-4, 1e-4))
          for r in random.sample(rows, 200)]
points += [(2.2099, 48.7099), (5.0, 46.0), (0.0, 0.0)]
json.dump({"find": cases, "near": points}, sys.stdout, ensure_ascii=False, indent=0)
