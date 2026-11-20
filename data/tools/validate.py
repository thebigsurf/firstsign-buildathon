"""Validate every file in data/: schema, foreign keys, sample paths, and the seeded event story.

Usage:  python data/tools/validate.py     (exit code 1 on any failure)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent
FORMS = {"tablet", "syrup", "sachet", "drops", "inhaler", "respule", "cream", "injection"}
UNITS = {"strip", "box", "bottle", "sachet", "tube", "vial"}
errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, dtype={"pin": str}, keep_default_na=False)


def main() -> int:
    groups = json.loads((DATA / "groups.json").read_text(encoding="utf-8"))
    gids = {g["id"] for g in groups}
    check(gids == {"fever", "diarrhoea", "respiratory", "allergy", "heat", "fungal", "eye", "tb_watch",
                   "chronic_bp", "chronic_diabetes", "other"}, "groups.json ids differ from contract")
    check(all(set(g) == {"id", "label", "label_hi", "color_hint", "is_chronic"} for g in groups), "groups.json keys")

    cat = read("catalogue.csv")
    check(list(cat.columns) == ["sku_id", "brand", "strength", "form", "pack", "molecule", "group", "unit", "aliases"],
          "catalogue columns")
    check(cat.sku_id.is_unique, "duplicate sku_id")
    check(set(cat.form) <= FORMS, f"bad forms {set(cat.form) - FORMS}")
    check(set(cat.unit) <= UNITS, f"bad units {set(cat.unit) - UNITS}")
    check(set(cat.group) == gids, f"groups not all covered: {gids - set(cat.group)}")
    check((cat.aliases.str.count(r"\|") >= 2).all(), "every SKU needs at least 3 aliases")
    check((cat.aliases == cat.aliases.str.lower()).all(), "aliases must be lower case")
    for col in ("brand", "strength", "pack", "molecule"):
        check((cat[col].str.len() > 0).all(), f"empty {col}")
    sku_ids = set(cat.sku_id)
    alias_owner: dict[str, set[str]] = {}
    for _, r in cat.iterrows():
        for a in r.aliases.split("|"):
            alias_owner.setdefault(a.strip(), set()).add(r.sku_id)
    shared = {a: s for a, s in alias_owner.items() if len(s) > 1}
    print(f"catalogue: {len(cat)} SKUs, {sum(len(v) for v in alias_owner.values())} aliases, "
          f"{len(shared)} aliases shared between SKUs")

    pins = read("pincodes.csv")
    pin_set = set(pins.pin)
    check(len(pins) == 20 and pins.pin.is_unique, "pincodes count/unique")
    check(pins.lat.between(18.9, 19.2).all() and pins.lng.between(72.8, 73.0).all(), "pin coords outside Mumbai")

    chem = read("chemists.csv")
    check(len(chem) == 150 and chem.chemist_id.is_unique, "chemists count/unique")
    check(set(chem.pin) <= pin_set, "chemist pin missing from pincodes.csv")
    check(set(chem.language) <= {"hi", "mr", "en"} and set(chem.software) <= {"paper", "marg", "other"}, "chemist enums")
    check(chem.shop_name.is_unique, "duplicate shop names")
    check((chem.owner_first_name.str.split().str.len() == 1).all(), "owner must be a first name only")
    check((chem.software == "paper").mean() > 0.55, "most chemists should be on paper")

    dist = json.loads((DATA / "distributor.json").read_text(encoding="utf-8"))
    check(set(dist["chemist_ids"]) <= set(chem.chemist_id) and len(dist["chemist_ids"]) == 120, "distributor chemists")
    served = chem[chem.chemist_id.isin(dist["chemist_ids"])]
    check(served.groupby("pin").size().min() >= 4, "each pin needs at least 4 served chemists")

    asha = read("asha.csv")
    check(set(asha.pin) <= pin_set and set(asha.language) <= {"hi", "mr"} and len(asha) == 12, "asha.csv")
    loc = read("localities.csv")
    check(set(loc.pin) == pin_set and loc.locality_id.is_unique, "localities pins/unique")
    check(loc.groupby("pin").size().between(5, 8).all(), "5-8 localities per pin")

    hist = read("history.csv")
    check(list(hist.columns) == ["date", "pin", "group", "units", "chemists_ordering"], "history columns")
    check(hist.date.nunique() == 90 and hist.date.max() == "2026-11-19", "history must be 90 days ending 2026-11-19")
    check(set(hist.pin) == pin_set and set(hist.group) == gids, "history pin x group coverage")
    check(len(hist) == 90 * 20 * 11, "history must be complete (90 x 20 x 11)")
    check((hist.units >= 0).all() and (hist.chemists_ordering >= 0).all(), "negative history values")
    check((hist.chemists_ordering > 0).le(hist.units > 0).all(), "chemists_ordering>0 with zero units")
    n_served = served.groupby("pin").size()
    check((hist.chemists_ordering <= hist.pin.map(n_served)).all(), "chemists_ordering exceeds served chemists")

    hist["date"] = pd.to_datetime(hist.date)
    base = hist[(hist.date >= "2026-10-05") & (hist.date <= "2026-11-01")].groupby(["pin", "group"])
    recent = hist[hist.date >= "2026-11-14"].groupby(["pin", "group"])
    ratio = (recent.units.mean() / base.units.mean()).unstack()
    breadth = (recent.chemists_ordering.mean() / base.chemists_ordering.mean()).unstack()
    for pin in ("400070", "400024", "400022"):
        check(ratio.loc[pin, "diarrhoea"] >= 2.0, f"diarrhoea event too weak in {pin}: {ratio.loc[pin, 'diarrhoea']:.2f}")
        check(breadth.loc[pin, "diarrhoea"] >= 1.3, f"diarrhoea breadth too low in {pin}")
    others = ratio["diarrhoea"].drop(["400070", "400024", "400022", "400086", "400037"])
    check(others.max() < 1.6, f"diarrhoea noise too high outside event: {others.max():.2f}")
    check(ratio.loc["400086", "diarrhoea"] > 1.8 and breadth.loc["400086", "diarrhoea"] < 1.4,
          "decoy pin should show high volume and low breadth")
    fever = hist[hist.date >= "2026-11-10"].groupby(["pin", "group"]).units.mean() / base.units.mean()
    fever = fever.unstack()
    for pin in ("400088", "400043"):
        check(fever.loc[pin, "fever"] >= 1.5, f"fever event too weak in {pin}")
        check(fever.loc[pin, "respiratory"] < 1.8, f"respiratory should stay modest in {pin}")
    check(ratio["respiratory"].median() > 1.15, "citywide respiratory bump missing")
    chronic = ratio[["chronic_bp", "chronic_diabetes"]].stack()
    check(chronic.between(0.5, 1.5).all(), "chronic groups should be stable")
    print("event check: diarrhoea ratio", ratio.loc[["400070", "400024", "400022"], "diarrhoea"].round(2).to_dict(),
          "| decoy 400086", round(ratio.loc["400086", "diarrhoea"], 2), "breadth", round(breadth.loc["400086", "diarrhoea"], 2),
          "| fever", fever.loc[["400088", "400043"], "fever"].round(2).to_dict(),
          "| median respiratory", round(ratio["respiratory"].median(), 2))

    inbox = json.loads((DATA / "demo_inbox.json").read_text(encoding="utf-8"))
    check(len(inbox) == 10 and len({m["id"] for m in inbox}) == 10, "inbox size/unique")
    check(Counter(m["type"] for m in inbox) == {"voice": 4, "photo": 3, "text": 3}, "inbox type mix")
    all_status: list[str] = []
    not_available = 0
    for m in inbox:
        check(m["chemist_id"] in set(chem.chemist_id), f"{m['id']} chemist missing")
        check(set(m) == {"id", "chemist_id", "received_at", "type", "text", "media", "expected"}, f"{m['id']} keys")
        if m["type"] == "text":
            check(bool(m["text"]) and m["media"] is None, f"{m['id']} text fields")
        else:
            check(m["text"] is None and (DATA / m["media"]).stat().st_size > 5000, f"{m['id']} media missing")
        exp = json.loads((DATA / m["expected"]).read_text(encoding="utf-8"))
        check(exp["chemist_id"] == m["chemist_id"] and exp["message_id"] == m["id"], f"{m['id']} expected ids")
        not_available += len(exp["not_available"])
        for ln in exp["lines"]:
            all_status.append(ln["status"])
            check(ln["group"] in gids | {None}, f"{m['id']} bad group")
            check(ln["sku_id"] in sku_ids | {None}, f"{m['id']} bad sku_id")
            check(all(a["sku_id"] in sku_ids for a in ln["alternatives"]), f"{m['id']} bad alternative")
            check((ln["status"] == "unknown") == (ln["sku_id"] is None), f"{m['id']} unknown/sku mismatch")
            check((ln["status"] == "matched") == (not ln["alternatives"]), f"{m['id']} alternatives/status mismatch")
            check(ln["qty"] > 0 and 0 <= ln["confidence"] <= 1, f"{m['id']} qty/confidence")
    c = Counter(all_status)
    check(c["uncertain"] >= 2 and c["unknown"] >= 1, "need ambiguous lines")
    check(not_available >= 1, "need a not-available mention")
    print("inbox line statuses:", dict(c), "| not_available mentions:", not_available)

    loc_ids = set(loc.locality_id)
    for exp_path in sorted((DATA / "samples").glob("asha_*.expected.json")):
        rep = json.loads(exp_path.read_text(encoding="utf-8"))
        check(rep["asha_id"] in set(asha.asha_id) and rep["locality_id"] in loc_ids, f"{exp_path.name} FK")
        check(rep["locality_id"].split("-")[0] == asha.set_index("asha_id").loc[rep["asha_id"], "pin"],
              f"{exp_path.name} ASHA and locality in different pins")
        check((exp_path.with_suffix("").with_suffix(".mp3")).exists(), f"{exp_path.name} audio missing")
    check(len(list((DATA / "samples").glob("asha_*.mp3"))) >= 3, "need ASHA voice notes")

    for e in errors:
        print("FAIL:", e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
