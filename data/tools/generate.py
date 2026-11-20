"""Generate the FirstSign simulated seed dataset (everything in data/ except media).

Usage:  python data/tools/generate.py
Deterministic: a fixed seed means the same files every run. All data is simulated.
Media (audio, handwritten photos) is produced by make_media.py from the files written here.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from catalogue_source import CATALOGUE_TEXT
from geo_source import (ASHAS, LOCALITIES, OWNER_FIRST_NAMES, PINCODES, SHOP_PREFIX, SHOP_TYPE)
from messages_source import ASHA_REPORTS, ORDERS

DATA_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = DATA_DIR / "samples"
SEED = 20261119
END_DATE = date(2026, 11, 19)
DAYS = 90

GROUPS = [
    ("fever", "Fever", "बुखार", "#e11d48", False),
    ("diarrhoea", "Diarrhoea and vomiting", "दस्त और उल्टी", "#0284c7", False),
    ("respiratory", "Cough, cold and breathing", "खाँसी, सर्दी और साँस", "#7c3aed", False),
    ("allergy", "Allergy", "एलर्जी", "#d97706", False),
    ("heat", "Heat and dehydration", "गर्मी और पानी की कमी", "#ea580c", False),
    ("fungal", "Skin fungal infection", "त्वचा का फंगल संक्रमण", "#65a30d", False),
    ("eye", "Eye infection", "आँख का संक्रमण", "#0d9488", False),
    ("tb_watch", "TB watch", "टीबी निगरानी", "#9f1239", False),
    ("chronic_bp", "Blood pressure and heart (chronic)", "बीपी और दिल (दीर्घकालिक)", "#475569", True),
    ("chronic_diabetes", "Diabetes (chronic)", "मधुमेह (दीर्घकालिक)", "#64748b", True),
    ("other", "Other", "अन्य", "#94a3b8", False),
]
GROUP_IDS = [g[0] for g in GROUPS]

# Baseline per chemist per day: (orders per day, mean units per order)
BASE_RATE = {
    "fever": (0.50, 13), "diarrhoea": (0.35, 15), "respiratory": (0.90, 7), "allergy": (0.40, 6),
    "heat": (0.12, 5), "fungal": (0.30, 3), "eye": (0.15, 3), "tb_watch": (0.05, 3),
    "chronic_bp": (0.75, 14), "chronic_diabetes": (0.65, 12), "other": (1.40, 9),
}
# Season factor at the start and end of the 90 days (late monsoon to mid November).
SEASON = {
    "fever": (1.30, 1.00), "diarrhoea": (1.25, 1.00), "respiratory": (0.90, 1.05), "allergy": (1.00, 1.00),
    "heat": (0.60, 0.50), "fungal": (1.30, 1.00), "eye": (1.40, 1.00), "tb_watch": (1.0, 1.0),
    "chronic_bp": (1.0, 1.0), "chronic_diabetes": (1.0, 1.0), "other": (1.0, 1.0),
}
CHRONIC = {"chronic_bp", "chronic_diabetes"}
DOW_FACTOR = [1.20, 1.05, 1.00, 1.00, 1.00, 0.90, 0.45]  # Monday to Sunday

# Seeded events (see data/README.md)
DIARRHOEA_PINS = {"400070": 0.85, "400024": 0.85, "400022": 0.85, "400037": 0.5}
DIARRHOEA_PEAK = {"400070": 3.6, "400024": 3.6, "400022": 3.6, "400037": 2.0}
DIARRHOEA_RAMP = [0.25, 0.55, 0.80, 1.0, 1.0, 0.95]  # 14 to 19 Nov
FEVER_PINS = {"400088": 0.95, "400043": 0.95}
FEVER_PEAK = 2.9
FEVER_DAYS = 10  # 10 to 19 Nov
AIR_RAMP = [0.4, 0.8, 1.0, 1.0, 1.0, 1.0, 0.8, 0.5, 0.3, 0.15]  # 10 to 19 Nov
AIR_PEAK = 1.5
DECOY_PIN = "400086"
DECOY_ORS_DAYS = {date(2026, 11, 13): 140, date(2026, 11, 15): 120, date(2026, 11, 17): 150, date(2026, 11, 18): 130}


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_catalogue() -> tuple[list[dict], dict[str, dict]]:
    rows: list[dict] = []
    by_key: dict[str, dict] = {}
    for line in CATALOGUE_TEXT.strip().splitlines():
        parts = line.split(";")
        if len(parts) != 9:
            raise ValueError(f"Bad catalogue line ({len(parts)} fields): {line[:60]}")
        key, brand, strength, form, pack, molecule, group, unit, aliases = parts
        row = {"sku_id": f"SKU{len(rows) + 1:04d}", "brand": brand, "strength": strength, "form": form,
               "pack": pack, "molecule": molecule, "group": group, "unit": unit, "aliases": aliases}
        if key in by_key:
            raise ValueError(f"Duplicate catalogue key {key}")
        rows.append(row)
        by_key[key] = row
    return rows, by_key


def largest_remainder(weights: list[float], total: int, minimum: int) -> list[int]:
    """Split `total` across weights, giving each at least `minimum`."""
    spare = total - minimum * len(weights)
    s = sum(weights)
    raw = [w / s * spare for w in weights]
    out = [minimum + int(r) for r in raw]
    order = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    for i in order[: total - sum(out)]:
        out[i] += 1
    return out


def build_chemists(rng: np.random.RandomState) -> list[dict]:
    counts = largest_remainder([p[5] for p in PINCODES], 150, 5)
    names_used: set[str] = set()
    chemists: list[dict] = []
    for (pin, area, _ward, lat, lng, _pop, default_lang), n in zip(PINCODES, counts):
        for _ in range(n):
            while True:
                shop = f"{SHOP_PREFIX[rng.randint(len(SHOP_PREFIX))]} {SHOP_TYPE[rng.randint(len(SHOP_TYPE))]}"
                if shop not in names_used:
                    names_used.add(shop)
                    break
            r = rng.rand()
            if default_lang == "en":
                language = "en" if r < 0.45 else "hi"
            else:
                language = default_lang if r < 0.75 else ("hi" if default_lang == "mr" else "mr") if r < 0.93 else "en"
            r = rng.rand()
            software = "paper" if r < 0.65 else "marg" if r < 0.87 else "other"
            chemists.append({
                "chemist_id": f"CH{len(chemists) + 1:03d}", "shop_name": shop,
                "owner_first_name": OWNER_FIRST_NAMES[rng.randint(len(OWNER_FIRST_NAMES))], "pin": pin,
                "area": area, "lat": round(lat + rng.uniform(-0.0055, 0.0055), 5),
                "lng": round(lng + rng.uniform(-0.0055, 0.0055), 5), "language": language, "software": software,
            })
    return chemists


def pick_served(chemists: list[dict], rng: np.random.RandomState) -> list[str]:
    """Choose 120 of 150 chemists, keeping at least 4 in every pin and the decoy shop's pin well covered."""
    served: list[str] = []
    rest: list[str] = []
    for pin, *_ in PINCODES:
        ids = [c["chemist_id"] for c in chemists if c["pin"] == pin]
        rng.shuffle(ids)
        keep = max(4, round(len(ids) * 0.8))
        served += ids[:keep]
        rest += ids[keep:]
    rng.shuffle(rest)
    while len(served) < 120:
        served.append(rest.pop())
    if len(served) > 120:
        by_pin: dict[str, list[str]] = {}
        id_pin = {c["chemist_id"]: c["pin"] for c in chemists}
        for cid in served:
            by_pin.setdefault(id_pin[cid], []).append(cid)
        while len(served) > 120:
            pin = max(by_pin, key=lambda p: len(by_pin[p]))
            served.remove(by_pin[pin].pop())
    return sorted(served)


def draw_orders(rng: np.random.RandomState, expected: float) -> int:
    """Order count with the right mean but less spread than Poisson (a chemist orders on a rhythm)."""
    whole = int(expected)
    return whole + int(rng.rand() < expected - whole)


def ramp_value(ramp: list[float], idx: int) -> float:
    return ramp[idx] if 0 <= idx < len(ramp) else 0.0


def build_history(chemists: list[dict], served: list[str], rng: np.random.RandomState) -> tuple[list[list], str]:
    by_id = {c["chemist_id"]: c for c in chemists}
    served_chemists = [by_id[c] for c in served]
    size = {c["chemist_id"]: float(np.exp(rng.normal(0, 0.35))) for c in served_chemists}
    affinity = {(c["chemist_id"], g): float(np.exp(rng.normal(0, 0.25))) for c in served_chemists for g in GROUP_IDS}

    # Which chemists are caught up in each event, fixed per event.
    diarrhoea_hit = {c["chemist_id"] for c in served_chemists
                     if c["pin"] in DIARRHOEA_PINS and rng.rand() < DIARRHOEA_PINS[c["pin"]]}
    fever_hit = {c["chemist_id"] for c in served_chemists
                 if c["pin"] in FEVER_PINS and rng.rand() < FEVER_PINS[c["pin"]]}
    air_hit = {c["chemist_id"] for c in served_chemists if rng.rand() < 0.9}
    decoy_chemist = max((c for c in served_chemists if c["pin"] == DECOY_PIN), key=lambda c: size[c["chemist_id"]])

    days = [END_DATE - timedelta(days=DAYS - 1 - i) for i in range(DAYS)]
    rows: list[list] = []
    for di, d in enumerate(days):
        frac = di / (DAYS - 1)
        dow = DOW_FACTOR[d.weekday()]
        month_end = d.day >= 28 or d.day <= 1
        tally: dict[tuple[str, str], list[int]] = {}
        for c in served_chemists:
            cid, pin = c["chemist_id"], c["pin"]
            for g in GROUP_IDS:
                base_orders, mean_qty = BASE_RATE[g]
                s0, s1 = SEASON[g]
                lam = base_orders * size[cid] * affinity[(cid, g)] * dow * (s0 + (s1 - s0) * frac)
                if month_end:
                    lam *= 1.35 if g in CHRONIC else 1.15
                mult = 1.0
                if g == "diarrhoea" and cid in diarrhoea_hit and d.month == 11 and 14 <= d.day <= 19:
                    mult = 1 + (DIARRHOEA_PEAK[pin] - 1) * ramp_value(DIARRHOEA_RAMP, d.day - 14)
                elif g == "fever" and cid in fever_hit and d.month == 11 and 10 <= d.day <= 19:
                    mult = 1 + (FEVER_PEAK - 1) * (0.2 + 0.8 * (d.day - 10) / (FEVER_DAYS - 1))
                elif g == "respiratory" and cid in air_hit and d.month == 11 and 10 <= d.day <= 19:
                    mult = 1 + (AIR_PEAK - 1) * ramp_value(AIR_RAMP, d.day - 10)
                n_orders = draw_orders(rng, lam * mult ** 0.6)
                units = 0
                for _ in range(n_orders):
                    units += max(1, int(round(mean_qty * np.exp(rng.normal(0, 0.3)) * mult ** 0.4)))
                if cid == decoy_chemist["chemist_id"] and g == "diarrhoea" and d in DECOY_ORS_DAYS:
                    units += DECOY_ORS_DAYS[d]
                    n_orders = max(n_orders, 1)
                cell = tally.setdefault((pin, g), [0, 0])
                cell[0] += units
                cell[1] += 1 if n_orders > 0 else 0
        for (pin, g), (units, ordering) in sorted(tally.items()):
            rows.append([d.isoformat(), pin, g, units, ordering])
    return rows, decoy_chemist["chemist_id"]


def build_localities(rng: np.random.RandomState) -> tuple[list[list], dict[tuple[str, str], str]]:
    pin_ll = {p[0]: (p[3], p[4]) for p in PINCODES}
    rows: list[list] = []
    lookup: dict[tuple[str, str], str] = {}
    for pin, locs in LOCALITIES.items():
        lat, lng = pin_ll[pin]
        for i, (name, landmark, households) in enumerate(locs, start=1):
            lid = f"{pin}-{i:02d}"
            lookup[(pin, name)] = lid
            rows.append([pin, lid, name, landmark, round(lat + rng.uniform(-0.005, 0.005), 5),
                         round(lng + rng.uniform(-0.005, 0.005), 5), households])
    return rows, lookup


def order_line(spec: dict, cat: dict[str, dict]) -> dict:
    sku = cat[spec["key"]] if spec["key"] else None
    return {
        "raw_text": spec["raw"],
        "sku_id": sku["sku_id"] if sku else None,
        "brand": sku["brand"] if sku else None,
        "strength": sku["strength"] if sku else None,
        "form": sku["form"] if sku else None,
        "molecule": sku["molecule"] if sku else None,
        "group": sku["group"] if sku else None,
        "qty": spec["qty"],
        "unit": spec["unit"] or (sku["unit"] if sku else "unit"),
        "confidence": spec["conf"],
        "status": spec["status"],
        "alternatives": [{"sku_id": cat[k]["sku_id"], "brand": cat[k]["brand"], "score": s} for k, s in spec["alts"]],
    }


def main() -> None:
    rng = np.random.RandomState(SEED)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    cat_rows, cat = build_catalogue()
    write_csv(DATA_DIR / "catalogue.csv",
              ["sku_id", "brand", "strength", "form", "pack", "molecule", "group", "unit", "aliases"],
              [[r[k] for k in ("sku_id", "brand", "strength", "form", "pack", "molecule", "group", "unit", "aliases")]
               for r in cat_rows])
    write_json(DATA_DIR / "groups.json",
               [{"id": g[0], "label": g[1], "label_hi": g[2], "color_hint": g[3], "is_chronic": g[4]} for g in GROUPS])
    write_csv(DATA_DIR / "pincodes.csv", ["pin", "area", "ward", "lat", "lng", "population"],
              [[p[0], p[1], p[2], p[3], p[4], p[5]] for p in PINCODES])

    chemists = build_chemists(rng)
    served = pick_served(chemists, rng)
    history, decoy_id = build_history(chemists, served, rng)
    loc_rows, loc_lookup = build_localities(rng)

    # Pick distinct chemists for the inbox. Language is set on the chosen chemist when none matches.
    used: set[str] = set()
    served_set = set(served)
    inbox: list[dict] = []
    for spec in ORDERS:
        pool = [c for c in chemists if c["pin"] == spec["pin"] and c["chemist_id"] in served_set
                and c["chemist_id"] not in used and c["chemist_id"] != decoy_id]
        match = [c for c in pool if c["language"] == spec["lang"]]
        chosen = (match or pool)[0]
        chosen["language"] = spec["lang"]
        used.add(chosen["chemist_id"])
        spec["chemist_id"] = chosen["chemist_id"]
    write_csv(DATA_DIR / "chemists.csv",
              ["chemist_id", "shop_name", "owner_first_name", "pin", "lat", "lng", "language", "software"],
              [[c[k] for k in ("chemist_id", "shop_name", "owner_first_name", "pin", "lat", "lng", "language", "software")]
               for c in chemists])
    write_json(DATA_DIR / "distributor.json", {
        "distributor_id": "DIST01",
        "name": "Sai Krupa Pharma Distributors",
        "address": "Dava Bazaar, Masjid Bunder, Mumbai (fictional demo distributor)",
        "area_served": "Kurla, Sion, Chembur, Ghatkopar, Dharavi, Bandra and Andheri belt",
        "pin_codes": sorted({c["pin"] for c in chemists if c["chemist_id"] in served_set}),
        "chemist_ids": served,
        "simulated": True,
    })
    write_csv(DATA_DIR / "history.csv", ["date", "pin", "group", "units", "chemists_ordering"], history)
    write_csv(DATA_DIR / "asha.csv", ["asha_id", "first_name", "pin", "language"], [list(a) for a in ASHAS])
    write_csv(DATA_DIR / "localities.csv",
              ["pin", "locality_id", "name", "landmark", "lat", "lng", "households"], loc_rows)

    for spec in ORDERS:
        expected_name = f"{spec['id'].replace('msg_', 'order_')}.expected.json"
        parsed = {
            "message_id": spec["id"], "chemist_id": spec["chemist_id"],
            "language": spec.get("language", spec["lang"]), "transcript": spec["transcript"],
            "lines": [order_line(ln, cat) for ln in spec["lines"]],
            "not_available": spec["not_available"], "notes": spec["notes"],
            "model": "ground_truth", "latency_ms": 0,
        }
        write_json(SAMPLES_DIR / expected_name, parsed)
        inbox.append({
            "id": spec["id"], "chemist_id": spec["chemist_id"],
            "received_at": f"2026-11-20T{spec['time']}:00+05:30", "type": spec["type"],
            "text": spec.get("text"), "media": f"samples/{spec['media']}" if spec["media"] else None,
            "expected": f"samples/{expected_name}",
        })
    write_json(DATA_DIR / "demo_inbox.json", inbox)

    asha_pin = {a[0]: a[2] for a in ASHAS}
    for spec in ASHA_REPORTS:
        if asha_pin[spec["asha_id"]] != spec["pin"]:
            raise ValueError(f"{spec['asha_id']} is not in pin {spec['pin']}")
        report = {
            "asha_id": spec["asha_id"], "locality_id": loc_lookup[(spec["pin"], spec["locality"])],
            "language": spec["language"], "transcript": spec["transcript"],
            **{k: spec[k] for k in ("households_visited", "fever", "diarrhoea", "cough", "breathing", "rash",
                                    "children_affected", "referred", "water_issue_reported", "notes")},
        }
        write_json(SAMPLES_DIR / spec["file"].replace(".mp3", ".expected.json"), report)

    print(f"catalogue {len(cat_rows)} | chemists {len(chemists)} (served {len(served)}) | "
          f"history rows {len(history)} | localities {len(loc_rows)} | decoy chemist {decoy_id}")


if __name__ == "__main__":
    main()
