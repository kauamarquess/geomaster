"""Valida os dados do Modo História. Uso (na pasta principal do projeto): python story/tools/validate_story_data.py"""
import json
from pathlib import Path

STORY = Path(__file__).resolve().parent.parent
ROOT = STORY.parent
errors = []
def check(ok, msg):
    if not ok: errors.append(msg)

world = json.loads((STORY / "data/world-order.json").read_text(encoding="utf-8"))
powers = json.loads((STORY / "data/powers.json").read_text(encoding="utf-8"))
names = json.loads((STORY / "data/country-names.json").read_text(encoding="utf-8"))
geo_ids = {f["properties"]["id"] for f in json.loads((ROOT / "data/geojson/countries.geojson").read_text(encoding="utf-8"))["features"]}

listed = [c for region in world["order"] for c in region["countries"]]
check(len(listed) == len(set(listed)), "país repetido em world-order.json")
check(set(listed) | set(world["excluded"]) == geo_ids, "world-order.json não cobre exatamente os países do GeoJSON")

check(set(names) == set(listed), "country-names.json precisa ter exatamente os países de world-order.json")

done = 0
rewards = []
invented = 0
for path in sorted((STORY / "data/countries").glob("*.json")):
    country = json.loads(path.read_text(encoding="utf-8")); cid = country["id"]; done += 1
    check(cid == path.stem and cid in listed, f"{path.name}: id inválido")
    stages = country["stages"]
    check([s["stage"] for s in stages] == list(range(1, 11)), f"{cid}: precisa de 10 fases numeradas de 1 a 10")
    for s in stages:
        check(bool(s["monster"].get("name") and s["monster"].get("legend")), f"{cid} fase {s['stage']}: monstro sem nome/lenda")
        check(len(s["monster"]["legend"]) <= 92, f"{cid} fase {s['stage']}: lenda longa demais para a tela (máx. 92 caracteres)")
        invented += bool(s["monster"].get("invented"))
        check(bool(s.get("boss")) == (s["stage"] == 10), f"{cid} fase {s['stage']}: só a fase 10 é boss")
    check(stages[-1].get("rewardPower") in powers, f"{cid}: poder do boss não existe em powers.json")
    rewards.append(stages[-1].get("rewardPower"))

repeated = len(rewards) - len(set(rewards))
print(f"{repeated} bosses repetem um poder (quem repete sobe o nível do poder)")
print(f"{invented} monstros inventados (marcados com invented: true)")
print(f"{len(listed)} países na ordem do mundo; {done} com fases prontas; {len(errors)} erro(s)")
for e in errors: print(" -", e)
raise SystemExit(1 if errors else 0)
