"""Gera data/country-info.json e data/question-countries.json a partir do banco e do GeoJSON.
Uso (na pasta principal do projeto): python scripts/build-country-info.py"""
import json, re, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()).strip()

geo = json.loads((ROOT / "data/geojson/countries.geojson").read_text(encoding="utf-8"))
countries = {f["properties"]["id"]: f["properties"] for f in geo["features"]}
by_name = {}
for cid, p in countries.items():
    by_name.setdefault(norm(p["name"]), cid)
    by_name.setdefault(norm(p["name_en"]), cid)

bank = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))
questions = bank["questions"] if isinstance(bank, dict) else bank

# Nomes mais longos primeiro: "Guiné-Bissau" vence "Guiné".
names_sorted = sorted(by_name, key=len, reverse=True)
def find_country(text):
    t = f" {norm(text)} "
    for n in names_sorted:
        if f" {n} " in t:
            return by_name[n]
    return None

info = {cid: {"name": p["name"], "nameEn": p["name_en"], "continent": p["continent"]} for cid, p in countries.items()}
neighbors = defaultdict(list)
qmap, unmatched = {}, []
for q in questions:
    if q["type"] in ("map", "flag"):
        continue
    cid = find_country(q["text"])
    if not cid:
        unmatched.append(q["id"]); continue
    qmap[q["id"]] = cid
    ex, cat, right = q.get("explanation", ""), q["category"], q["options"][q["correctIndex"]]
    if cat == "capitals": info[cid]["capital"] = right
    elif cat == "culture": info[cid]["currency"] = right
    elif cat == "continents": info[cid]["subregion"] = right
    elif cat == "borders": neighbors[cid].append(right)
for cid, lst in neighbors.items():
    info[cid]["neighbors"] = sorted(set(lst))

(ROOT / "data/country-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
(ROOT / "data/question-countries.json").write_text(json.dumps(qmap, ensure_ascii=False, sort_keys=True), encoding="utf-8")
print(f"perguntas ligadas a países: {len(qmap)}; sem país: {len(unmatched)} {unmatched[:15]}")
for k in ("capital", "currency", "subregion", "neighbors"):
    print(k, sum(1 for v in info.values() if k in v), "de", len(info))
