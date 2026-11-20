"""Generate the EXTENDED simulated dataset for FirstSign into data/extended/.

Deterministic (fixed seed). Never touches the base files; it only READS them.
Usage:  python data/tools/generate_extended.py [--refresh-weather]

Real data: environment_daily.csv (Open-Meteo, cached in extended/_cache/ so reruns
are offline and identical).  Everything else is SIMULATED.  See extended/README.md.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261121
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "extended"
CACHE = OUT / "_cache"
OUT.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)

AS_OF = pd.Timestamp("2026-11-19")
TODAY = pd.Timestamp("2026-11-21")
DATES = pd.date_range("2026-08-22", "2026-11-19")
DECOY_CHEMIST = "CH082"
DECOY_DATES = {pd.Timestamp(d) for d in ("2026-11-13", "2026-11-15", "2026-11-17", "2026-11-18")}
ORS_SKUS = ["SKU0021", "SKU0022"]


import time
_T0 = time.time()


def log(*a):
    print(f"[{time.time() - _T0:6.0f}s]", *a, flush=True)


# --------------------------------------------------------------------------- base
cat = pd.read_csv(ROOT / "catalogue.csv")
hist = pd.read_csv(ROOT / "history.csv", parse_dates=["date"])
chem_all = pd.read_csv(ROOT / "chemists.csv")
dist = json.load(open(ROOT / "distributor.json", encoding="utf-8"))
asha = pd.read_csv(ROOT / "asha.csv")
loc = pd.read_csv(ROOT / "localities.csv")
pins = pd.read_csv(ROOT / "pincodes.csv")
chem = chem_all[chem_all.chemist_id.isin(dist["chemist_ids"])].reset_index(drop=True)
CIDX = {c: i for i, c in enumerate(chem.chemist_id)}
GROUPS = [g["id"] for g in json.load(open(ROOT / "groups.json", encoding="utf-8"))]
GIDX = {g: i for i, g in enumerate(GROUPS)}
cat = cat.set_index("sku_id", drop=False)
for _c in ["brand", "strength", "form", "molecule", "group", "unit", "pack", "aliases"]:
    globals()["CAT_" + _c.upper()] = cat[_c].astype(str).to_dict()
SKUS = list(cat.sku_id)
SIDX = {s: i for i, s in enumerate(SKUS)}
sku_by_group = {g: [s for s in SKUS if CAT_GROUP[s] == g] for g in GROUPS}
pin_pop = dict(zip(pins.pin, pins.population))
served_by_pin = {int(p): list(d.chemist_id) for p, d in chem.groupby("pin")}

# --------------------------------------------------------------------------- staff
SALESMAN_NAMES = ["Imran", "Santosh", "Rajesh", "Faisal", "Dinesh", "Prakash", "Ashok", "Vikas", "Sachin", "Rafiq"]
BEATS = [(400070, 400024), (400022, 400037), (400017, 400019), (400031, 400071), (400088, 400043),
         (400086, 400077), (400072, 400093), (400050, 400051), (400055, 400069), (400058, 400076)]
BEAT_DAYS = ["Mon|Thu", "Tue|Fri", "Wed|Sat", "Mon|Thu", "Tue|Fri", "Wed|Sat", "Mon|Thu", "Tue|Fri", "Wed|Sat", "Tue|Sat"]
CLERK_NAMES = ["Aman", "Meena", "Pooja", "Ketan", "Sunil", "Rohan"]
staff_rows = []
for i, (n, b, d) in enumerate(zip(SALESMAN_NAMES, BEATS, BEAT_DAYS), 1):
    staff_rows.append(dict(salesman_id=f"SM{i:02d}", first_name=n, role="salesman",
                           beat_pins="|".join(map(str, b)), beat_days=d))
for i, n in enumerate(CLERK_NAMES, 1):
    staff_rows.append(dict(salesman_id=f"CK{i:02d}", first_name=n, role="order_clerk", beat_pins="", beat_days=""))
salesmen = pd.DataFrame(staff_rows)
pin_salesman = {}
for i, b in enumerate(BEATS, 1):
    for p in b:
        pin_salesman[p] = f"SM{i:02d}"

# --------------------------------------------------------------------------- prices (needed for claims)
def make_prices():
    rows = []
    r = np.random.default_rng(SEED + 1)
    for s in SKUS:
        form, unit, group = CAT_FORM[s], CAT_UNIT[s], CAT_GROUP[s]
        if form == "tablet":
            mrp = r.lognormal(np.log(48), 0.7)
        elif form == "syrup":
            mrp = r.lognormal(np.log(95), 0.45)
        elif form == "sachet":
            mrp = r.lognormal(np.log(22), 0.4)
        elif form == "inhaler":
            mrp = r.lognormal(np.log(210), 0.4)
        elif form == "respule":
            mrp = r.lognormal(np.log(120), 0.3)
        elif form == "injection":
            mrp = r.lognormal(np.log(85), 0.5)
        elif form == "cream":
            mrp = r.lognormal(np.log(80), 0.4)
        else:
            mrp = r.lognormal(np.log(70), 0.4)
        if s in ORS_SKUS:
            mrp = 21.0 if s == "SKU0021" else 24.0
        if group == "chronic_bp" or group == "chronic_diabetes":
            mrp *= 1.5
        mrp = max(5.0, round(mrp * 2) / 2)
        rows.append(dict(sku_id=s, mrp_rs=mrp, ptr_rs=round(mrp * 0.80, 2)))
    return pd.DataFrame(rows)


prices = make_prices()
PTR = dict(zip(prices.sku_id, prices.ptr_rs))

# --------------------------------------------------------------------------- chemist profiles
n_ch = len(chem)
size_w = rng.lognormal(0.0, 0.85, n_ch)  # heavy-tailed shop size
affin = rng.lognormal(0.0, 0.45, (n_ch, len(GROUPS)))
pref = rng.lognormal(0.0, 0.7, (n_ch, len(SKUS)))
# global SKU popularity inside each group (Zipf-like on a random order)
sku_pop = np.ones(len(SKUS))
for g, lst in sku_by_group.items():
    order = rng.permutation(len(lst))
    for rank, j in enumerate(order):
        sku_pop[SIDX[lst[j]]] = 1.0 / (1.0 + rank) ** 0.9
# make well-known leaders really lead
for s, m in [("SKU0001", 4.0), ("SKU0021", 2.0), ("SKU0016", 1.5)]:
    sku_pop[SIDX[s]] *= m

CHANNELS = ["voice_note", "photo", "whatsapp_text", "salesman", "phone_call", "app"]
MIX = {
    "paper": [0.30, 0.24, 0.06, 0.28, 0.12, 0.00],
    "marg": [0.12, 0.08, 0.22, 0.24, 0.08, 0.26],
    "other": [0.20, 0.12, 0.25, 0.20, 0.10, 0.13],
}
chem_mix = []
for _, r in chem.iterrows():
    p = np.array(MIX[r.software])
    if r.language == "en":
        p = p + np.array([-0.05, -0.04, 0.05, -0.02, 0.0, 0.06]) * (p > 0)
    p = np.clip(p, 0, None)
    p = p / p.sum()
    mix = rng.dirichlet(p * 10 + 1e-6)
    if p[5] == 0:
        mix[5] = 0
        mix = mix / mix.sum()
    chem_mix.append(mix)
chem_mix = np.array(chem_mix)

# --------------------------------------------------------------------------- scripted events (used by lines + ASHA + official)
# pharmacy start dates and per-pin lags come from the story in data/README.md
EV_DIARR_START = pd.Timestamp("2026-11-14")
EV_FEVER_START = pd.Timestamp("2026-11-10")
EVENTS = {
    "E1_diarrhoea_waterborne": dict(group="diarrhoea", syndrome="acute_diarrhoeal_disease", start=EV_DIARR_START,
        pins={400022: dict(asha_lag=3, off_lag=2, off_peak=3.2, asha_peak=12.0, hot=["01", "02", "06"]),
              400070: dict(asha_lag=4, off_lag=4, off_peak=2.6, asha_peak=11.0, hot=["01", "02", "03"]),
              400024: dict(asha_lag=5, off_lag=5, off_peak=2.4, asha_peak=11.0, hot=["02", "03"]),
              400037: dict(asha_lag=6, off_lag=6, off_peak=1.3, asha_peak=2.5, hot=["01"])}),
    "E2_dengue_like_fever": dict(group="fever", syndrome="fever_dengue_like", start=EV_FEVER_START,
        pins={400088: dict(asha_lag=5, off_lag=6, off_peak=2.6, asha_peak=8.0, hot=["02", "04", "06"]),
              400043: dict(asha_lag=4, off_lag=4, off_peak=2.3, asha_peak=7.5, hot=["01", "03", "06"])}),
}


def ramp(t, start, lag, ramp_days):
    d = (t - start).days - lag
    if d < 0:
        return 0.0
    return min(1.0, (d + 1) / ramp_days)


# ============================================================================ 1. ORDER LINES
log("[1] allocating history units to chemists, lines, orders ...")
h = hist[hist.units > 0].copy()
med60 = hist[hist.date < "2026-10-20"].groupby(["pin", "group"]).units.median().to_dict()

lines = []  # dicts
for row in h.itertuples(index=False):
    pin, g, U, k = int(row.pin), row.group, int(row.units), int(row.chemists_ordering)
    ids = served_by_pin[pin]
    k = max(1, min(k, len(ids), U))
    gi = GIDX[g]
    idx = np.array([CIDX[c] for c in ids])
    w = size_w[idx] * affin[idx, gi]
    decoy = (pin == 400086 and g == "diarrhoea" and row.date in DECOY_DATES)
    surge = U > 1.8 * med60.get((row.pin, g), 1e9)
    if decoy:
        d_i = ids.index(DECOY_CHEMIST)
        others = [i for i in range(len(ids)) if i != d_i]
        pw = w[others] / w[others].sum()
        pick_o = list(rng.choice(others, size=k - 1, replace=False, p=pw)) if k > 1 else []
        picked = [d_i] + pick_o
        q82 = int(min(rng.integers(120, 151), U - (k - 1)))
        if k == 1:
            q82 = U
        rest = U - q82
        quant = [q82]
        if k > 1:
            pw2 = w[pick_o] * rng.gamma(2.0, 1.0, len(pick_o))
            quant += list(1 + rng.multinomial(rest - (k - 1), pw2 / pw2.sum()))
    else:
        picked = list(rng.choice(len(ids), size=k, replace=False, p=w / w.sum()))
        if k == 1:
            quant = [U]
        else:
            pw2 = w[picked] * rng.gamma(2.0, 1.0, k)
            quant = list(1 + rng.multinomial(U - k, pw2 / pw2.sum()))
    for ci_local, q in zip(picked, quant):
        cid = ids[ci_local]
        ci = CIDX[cid]
        if decoy and cid == DECOY_CHEMIST:
            lines.append(dict(date=row.date, chemist_id=cid, pin=pin, group=g, sku_id=str(rng.choice(ORS_SKUS, p=[0.7, 0.3])), qty=int(q), decoy=True))
            continue
        n = 1 + (q >= 30 and rng.random() < 0.5) + (q >= 80 and rng.random() < 0.6)
        n = int(min(n, q, len(sku_by_group[g])))
        cand = sku_by_group[g]
        cw = np.array([sku_pop[SIDX[s]] * pref[ci, SIDX[s]] for s in cand])
        if surge and g == "diarrhoea":
            cw = cw * np.array([4.0 if s in ("SKU0021", "SKU0022", "SKU0036", "SKU0031") else 1.0 for s in cand])
        if surge and g == "fever":
            cw = cw * np.array([2.5 if CAT_MOLECULE[s] == "Paracetamol" else 1.0 for s in cand])
        chosen = list(rng.choice(len(cand), size=n, replace=False, p=cw / cw.sum()))
        if n == 1:
            parts = [q]
        else:
            pr = rng.dirichlet(np.ones(n) * 1.5)
            parts = list(1 + rng.multinomial(q - n, pr))
        for j, qq in zip(chosen, parts):
            lines.append(dict(date=row.date, chemist_id=cid, pin=pin, group=g, sku_id=cand[j], qty=int(qq), decoy=False))

L = pd.DataFrame(lines)
log("   lines:", len(L))

# ---- orders: split each chemist-day into 1-3 orders
orders = []
line_order = np.zeros(len(L), dtype=int)
oid_tmp = 0
by_cd = L.groupby(["date", "chemist_id"]).indices
for (d, cid), ix in by_cd.items():
    ix = np.array(ix)
    ci = CIDX[cid]
    nl = len(ix)
    if nl <= 2:
        no = 1
    else:
        no = int(rng.choice([1, 2, 3], p=[0.62, 0.30, 0.08]))
        no = min(no, nl)
    assign = rng.integers(0, no, nl) if no > 1 else np.zeros(nl, dtype=int)
    for slot in range(no):
        sel = ix[assign == slot]
        if len(sel) == 0:
            continue
        ch = str(rng.choice(CHANNELS, p=chem_mix[ci]))
        pin = int(chem.loc[ci, "pin"])
        sunday = d.dayofweek == 6
        if ch == "salesman":
            hr = float(np.clip(rng.normal(17.0, 1.3), 13.5, 20.0))
            if sunday:
                hr = float(np.clip(rng.normal(11.5, 1.0), 9.5, 14.0))
        elif ch == "phone_call":
            hr = float(np.clip(rng.normal(12.5, 3.0), 8.5, 19.0))
        else:
            r = rng.random()
            if sunday:
                hr = float(np.clip(rng.normal(11.0, 1.2), 9.0, 14.0))
            elif r < 0.40:
                hr = float(np.clip(rng.normal(10.4, 0.9), 8.5, 12.8))
            elif r < 0.50:
                hr = float(np.clip(rng.normal(14.8, 1.4), 12.8, 18.0))
            else:
                hr = float(np.clip(rng.normal(21.9, 0.75), 20.0, 23.6))
        ts = d + pd.Timedelta(seconds=int(hr * 3600))
        orders.append(dict(tmp=oid_tmp, date=d, chemist_id=cid, pin=pin, received_at=ts, channel=ch,
                           salesman_id=pin_salesman[pin], n_lines=len(sel)))
        line_order[sel] = oid_tmp
        oid_tmp += 1
O = pd.DataFrame(orders).sort_values("received_at", kind="stable").reset_index(drop=True)
O["order_id"] = [f"ORD-{d:%Y%m%d}-{n:04d}" for d, n in zip(O.date, O.groupby("date").cumcount() + 1)]
tmp2oid = dict(zip(O.tmp, O.order_id))
tmp2rcv = dict(zip(O.tmp, O.received_at))
L["order_id"] = [tmp2oid[t] for t in line_order]
L["received_at"] = [tmp2rcv[t] for t in line_order]
L = L.sort_values(["received_at", "order_id"], kind="stable").reset_index(drop=True)
L["line_no"] = L.groupby("order_id").cumcount() + 1

# ============================================================================ schemes
log("[2] schemes ...")
brand_of = {s: CAT_BRAND[s] for s in SKUS}
scheme_rows = []
sc_pick = rng.choice(len(SKUS), 27, replace=False)
# decoy ORS scheme first
big_pool = [c for c in chem.chemist_id if chem.set_index("chemist_id").loc[c, "pin"] in (400086, 400077, 400071, 400072)]
elig_ors = sorted(set(big_pool[:14] + [DECOY_CHEMIST]))
scheme_rows.append(dict(scheme_id="SCH001", brand="ORS Sachet (WHO formula) / Electral Powder", sku_ids="|".join(ORS_SKUS),
                        offer="50+10", offer_type="free_goods", buy_qty=50, free_qty=10, min_qty=100, start="2026-11-12",
                        end="2026-11-20", eligible_chemists="|".join(elig_ors),
                        notes="Big-lot sachet scheme circulated to selected chemists; minimum 100 sachets. Drives the CH082 decoy bulk orders."))
offers = [("10+1", 10, 1), ("5+1", 5, 1), ("12+2", 12, 2), ("20+3", 20, 3), ("10+2", 10, 2), ("6+1", 6, 1)]
seen = set()
sn = 2
for i in sc_pick:
    s = SKUS[i]
    if CAT_GROUP[s] in ("chronic_bp", "chronic_diabetes", "tb_watch") and rng.random() < 0.5:
        continue
    if s in ORS_SKUS or brand_of[s].split()[0] in seen:
        continue
    seen.add(brand_of[s].split()[0])
    fam = [x for x in SKUS if brand_of[x].split()[0] == brand_of[s].split()[0]][:4]
    o = offers[int(rng.integers(len(offers)))]
    if rng.random() < 0.18:
        otype, offer, buy, free = "discount_pct", f"{int(rng.choice([5, 8, 10, 12]))}% extra", 0, 0
        minq = int(rng.choice([6, 10, 12]))
    else:
        otype, offer, buy, free = "free_goods", o[0], o[1], o[2]
        minq = buy
    st = pd.Timestamp("2026-08-22") + pd.Timedelta(days=int(rng.integers(-20, 70)))
    en = st + pd.Timedelta(days=int(rng.choice([30, 45, 60, 90])))
    elig = "ALL" if rng.random() < 0.65 else "|".join(sorted(rng.choice(chem.chemist_id, int(rng.integers(35, 90)), replace=False)))
    scheme_rows.append(dict(scheme_id=f"SCH{sn:03d}", brand=brand_of[s].split()[0], sku_ids="|".join(fam), offer=offer,
                            offer_type=otype, buy_qty=buy, free_qty=free, min_qty=minq, start=st.strftime("%Y-%m-%d"),
                            end=en.strftime("%Y-%m-%d"), eligible_chemists=elig,
                            notes="Trade scheme from the brand; conditions read from the scheme circular."))
    sn += 1
schemes = pd.DataFrame(scheme_rows)

# ============================================================================ stock simulation + line status
log("[3] stock simulation and line outcomes ...")
DISRUPT = {"SKU0021", "SKU0022", "SKU0036", "SKU0001", "SKU0003", "SKU0010"}
demand0 = L[L.date < "2026-09-19"].groupby("sku_id").qty.sum() / 28.0
avg0 = {s: float(demand0.get(s, 0.4)) for s in SKUS}
stock = {s: int(max(12, avg0[s] * rng.uniform(18, 26))) for s in SKUS}
init_stock = dict(stock)
pipeline = {s: [] for s in SKUS}  # (due_date, qty)
hist14 = {s: deque([avg0[s]] * 14, maxlen=14) for s in SKUS}
sch_cache = []
for r in scheme_rows:
    sch_cache.append((r["scheme_id"], set(r["sku_ids"].split("|")), pd.Timestamp(r["start"]), pd.Timestamp(r["end"]),
                      None if r["eligible_chemists"] == "ALL" else set(r["eligible_chemists"].split("|")),
                      r["min_qty"], r["buy_qty"], r["free_qty"], r["offer_type"]))

# helper: substitution candidates
def sub_candidates(sku):
    mol = CAT_MOLECULE[sku]
    g = CAT_GROUP[sku]
    same_mol = [s for s in sku_by_group[g] if s != sku and CAT_MOLECULE[s] == mol and CAT_FORM[s] == CAT_FORM[sku]]
    same_grp = [s for s in sku_by_group[g] if s != sku and CAT_FORM[s] == CAT_FORM[sku]]
    return same_mol or same_grp


n = len(L)
qty_sup = np.zeros(n, dtype=int)
short_q = np.zeros(n, dtype=int)
lstat = np.empty(n, dtype=object)
subsku = np.full(n, "", dtype=object)
scheme_app = np.full(n, "", dtype=object)
free_q = np.zeros(n, dtype=int)
reason = np.full(n, "", dtype=object)
stock_rows = []
disp_log = {s: defaultdict(int) for s in SKUS}  # dispatched per day
recv_log = {s: defaultdict(int) for s in SKUS}

day_idx = L.groupby(L.date.dt.normalize()).indices
A_SKU, A_QTY, A_DATE, A_CH = L.sku_id.to_numpy(), L.qty.to_numpy(), L.date.to_numpy(), L.chemist_id.to_numpy()
for d in DATES:
    # arrivals (no deliveries on Sunday: due dates were already shifted)
    opening = dict(stock)
    for s in SKUS:
        keep = []
        for due, q in pipeline[s]:
            if due <= d:
                stock[s] += q
                recv_log[s][d] += q
            else:
                keep.append((due, q))
        pipeline[s] = keep
    ix = day_idx.get(d, np.array([], dtype=int))
    dispatched = defaultdict(int)
    for i in ix:  # already in received_at order
        r_sku, q, d_, cid = A_SKU[i], int(A_QTY[i]), d, A_CH[i]
        # scheme
        for scid, sset, st, en, el, minq, buy, free, otype in sch_cache:
            if r_sku in sset and st <= d_ <= en and q >= minq and (el is None or cid in el):
                if scid == "SCH001" or rng.random() < 0.85:
                    scheme_app[i] = scid
                    if otype == "free_goods" and buy:
                        free_q[i] = (q // buy) * free
                    break
        roll = rng.random()
        avail = stock[r_sku]
        status, sup, sub, why = "supplied", q, "", ""
        if roll < 0.012:
            status, sup, why = "not_available", 0, "pack_not_stocked" if rng.random() < 0.5 else "supplier_delay"
        elif roll < 0.032 and q > 1:
            status, sup, why = "short", int(max(1, round(q * rng.uniform(0.4, 0.85)))), "short_supply"
        if avail <= 0:
            status, sup, why = "not_available", 0, "out_of_stock"
        elif avail < sup:
            status, sup, why = "short", avail, "out_of_stock"
        own_take = sup
        deficit = q - sup
        if status in ("not_available", "short") and rng.random() < 0.38:
            cands = [c for c in sub_candidates(r_sku) if stock[c] >= deficit]
            if cands:
                cw = np.array([sku_pop[SIDX[c]] for c in cands])
                s2 = cands[int(rng.choice(len(cands), p=cw / cw.sum()))]
                stock[s2] -= deficit
                dispatched[s2] += deficit
                sub = s2
                status = "substituted"
                sup = q
        stock[r_sku] -= own_take
        dispatched[r_sku] += own_take
        short_q[i] = deficit
        qty_sup[i] = sup
        lstat[i] = status
        subsku[i] = sub
        reason[i] = why
    # end of day: record, reorder
    for s in SKUS:
        dsp = dispatched[s]
        hist14[s].append(dsp)
        avg = max(0.3, float(np.mean(hist14[s])))
        recv = recv_log[s][d]
        t7 = list(hist14[s])[-7:]
        cover = round(stock[s] / max(0.3, float(np.mean(t7))), 1)
        onord = sum(q for _, q in pipeline[s])
        stock_rows.append(dict(date=d, sku_id=s, opening=opening[s], received=recv, dispatched=dsp, closing=stock[s],
                               days_of_cover=min(cover, 99.0), on_order=onord))
        lead_extra = 0
        rop_days = 11.0
        qmult = 16.0
        if (stock[s] + onord) < avg * rop_days:
            lead = int(rng.choice([3, 4, 4, 5, 6]))
            if rng.random() < 0.03:
                lead += int(rng.integers(3, 8))  # random supplier delay
            q = int(max(10, round(avg * qmult / 10.0) * 10))
            if s in DISRUPT and d >= pd.Timestamp("2026-11-03"):
                # company supply constraint: nothing placed from 3 Nov lands before about 22 Nov
                lead = (pd.Timestamp("2026-11-22") - d).days + int(rng.integers(0, 3))
            due = d + pd.Timedelta(days=lead)
            if due.dayofweek == 6:
                due += pd.Timedelta(days=1)
            pipeline[s].append((due, q))

L["qty_supplied"] = qty_sup
L["line_status"] = lstat
L["substituted_sku_id"] = subsku
L["scheme_applied"] = scheme_app
L["free_qty"] = free_q
L["reason"] = reason
L["short_q"] = short_q
stock_df = pd.DataFrame(stock_rows)

# ============================================================================ raw text
log("[4] raw text ...")
NUMW = {5: "paanch", 10: "das", 12: "barah", 15: "pandrah", 20: "bees", 25: "pachchis", 30: "tees", 50: "pachaas", 100: "sau"}
UNITW = {"strip": ["strip", "patta", "pkt"], "bottle": ["bottle", "syp", "shishi"], "sachet": ["sachet", "packet", "pkt"],
         "box": ["box", "dabba", "pkt"], "tube": ["tube", "pc"], "vial": ["vial", "inj", "pc"]}
FORM_PREFIX = {"tablet": "Tab", "syrup": "Syp", "inhaler": "Inh", "respule": "Resp", "drops": "Drops", "cream": "Cr",
               "injection": "Inj", "sachet": "Sach"}
VAGUE = {"fever": ["bukhar ki goli", "paracetamol wali", "bachchon ki bukhar wali syrup"],
         "diarrhoea": ["pet kharab wali dawai", "dast ki goli", "ORS wala packet"],
         "respiratory": ["khansi ki syrup", "cold wali goli", "dama wala pump"],
         "allergy": ["allergy ki goli", "khujli wali"],
         "other": ["wahi jo kal bheja tha", "woh gas wali goli", "dard ki goli"]}
alias_cache = {s: [a for a in str(CAT_ALIASES[s]).split("|") if a] or [CAT_BRAND[s].lower()] for s in SKUS}


def typo(s):
    if len(s) < 5 or rng.random() > 0.30:
        return s
    i = int(rng.integers(1, len(s) - 1))
    k = rng.random()
    if k < 0.4:
        return s[:i] + s[i + 1:]
    if k < 0.7 and s[i] != " " and s[i - 1] != " ":
        return s[:i - 1] + s[i] + s[i - 1] + s[i + 1:]
    return s[:i] + s[i] + s[i:]


def qword(q):
    return NUMW.get(q, str(q)) if rng.random() < 0.35 else str(q)


def make_raw(channel, sku, q, lang, group):
    if rng.random() < 0.025 and group in VAGUE:
        return f"{rng.choice(VAGUE[group])} {q}"
    al = str(rng.choice(alias_cache[sku]))
    unit = CAT_UNIT[sku]
    uw = str(rng.choice(UNITW.get(unit, [unit])))
    form = CAT_FORM[sku]
    if channel == "app":
        return f"{CAT_BRAND[sku]} {CAT_STRENGTH[sku]}".strip()
    if channel == "voice_note":
        al = typo(al)
        t = int(rng.integers(6))
        if lang == "mr":
            return [f"{al} {qword(q)} {uw} dya", f"{qword(q)} {al} pathva", f"{al} {qword(q)}", f"ek {al} {qword(q)} {uw}",
                    f"{al} {qword(q)} pahije", f"{al} {qword(q)} {uw} lagtil"][t]
        if lang == "en":
            return [f"{al} {q} {uw}", f"send {q} {al}", f"{al} {q}", f"{q} {uw} of {al}", f"{al} {q} nos", f"{al} x {q}"][t]
        return [f"{al} {qword(q)} {uw}", f"{qword(q)} {al}", f"{al} {qword(q)} bhej do", f"{al} ka {qword(q)} {uw}",
                f"{qword(q)} {uw} {al}", f"{al} {qword(q)} dedo"][t]
    if channel == "phone_call":
        t = int(rng.integers(3))
        return [f"{al} {qword(q)}", f"{al} {qword(q)} {uw}", f"{qword(q)} {al} chahiye"][t]
    if channel == "photo":
        al = typo(al)
        t = int(rng.integers(5))
        pre = FORM_PREFIX.get(form, "")
        return [f"{pre} {al.title()} - {q}", f"{al} {q}", f"{pre} {al} x{q}", f"{al.upper()} {q} {uw}", f"{al}  {q}{uw[:3]}"][t].strip()
    if channel == "whatsapp_text":
        t = int(rng.integers(4))
        return [f"{al} {q}", f"{q} {al}", f"{al} {q} {uw}", f"{al} - {q}"][t]
    # salesman sheet
    t = int(rng.integers(3))
    return [f"{al.upper()} {q} {uw.upper()}", f"{al.title()} {q}", f"{al} {q} {uw}"][t]


ord_ch = dict(zip(O.order_id, O.channel))
ord_lang = {}
cl = dict(zip(chem.chemist_id, chem.language))
ord_chem = dict(zip(O.order_id, O.chemist_id))
L["raw_text"] = [make_raw(ord_ch[o], s, q, cl[ord_chem[o]], g) for o, s, q, g in zip(L.order_id, L.sku_id, L.qty, L.group)]
L["unit"] = [CAT_UNIT[s] for s in L.sku_id]

# ============================================================================ order headers
log("[5] order headers ...")
ls = L.groupby("order_id").line_status.agg(list)
nl = L.groupby("order_id").size()
O["n_lines"] = O.order_id.map(nl)
O["status"] = [("billed" if all(x in ("supplied", "substituted") for x in ls[o]) else
                ("not_billed_no_stock" if all(x == "not_available" for x in ls[o]) else "partially_billed")) for o in O.order_id]
late = O.received_at >= pd.Timestamp("2026-11-19 21:00")
O.loc[late, "status"] = "approved"
clerk_w = np.array([0.3, 0.25, 0.2, 0.1, 0.1, 0.05])
O["approved_by"] = [str(rng.choice(CLERK_NAMES, p=clerk_w)) for _ in range(len(O))]
base_min = {"voice_note": (1.8, 0.9), "photo": (2.0, 0.8), "whatsapp_text": (0.8, 0.35), "salesman": (0.6, 0.4),
            "phone_call": (2.5, 0.7), "app": (0.2, 0.05)}
cmin = []
for ch, nln in zip(O.channel, O.n_lines):
    a, b = base_min[ch]
    cmin.append(round((a + b * nln) * rng.gamma(8, 1 / 8), 1))
O["clerk_minutes_estimate"] = cmin

orders_out = O[["order_id", "chemist_id", "pin", "received_at", "channel", "salesman_id", "status", "approved_by",
                "clerk_minutes_estimate"]].copy()
orders_out["received_at"] = orders_out.received_at.dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
orders_out.to_csv(OUT / "orders.csv", index=False)
lines_out = L[["order_id", "line_no", "raw_text", "sku_id", "qty", "unit", "scheme_applied", "line_status",
               "substituted_sku_id", "qty_supplied", "free_qty"]].sort_values(["order_id", "line_no"])
lines_out.to_csv(OUT / "order_lines.csv", index=False)
salesmen.to_csv(OUT / "salesmen.csv", index=False)
schemes.to_csv(OUT / "schemes.csv", index=False)
prices.to_csv(OUT / "sku_prices.csv", index=False)
stock_df.to_csv(OUT / "distributor_stock.csv", index=False)

# ---- reconciliation
rec = L.groupby(["date", "pin", "group"]).qty.sum().rename("lines_units").reset_index()
m = hist.merge(rec, on=["date", "pin", "group"], how="outer").fillna({"units": 0, "lines_units": 0})
m["diff"] = (m.units - m.lines_units).abs()
chk = L.groupby(["date", "pin", "group"]).chemist_id.nunique().rename("c").reset_index()
m2 = hist.merge(chk, on=["date", "pin", "group"], how="left").fillna({"c": 0})
RECON = dict(cells=int(len(m)), cells_exact=int((m["diff"] == 0).sum()), max_abs_diff=int(m["diff"].max()),
             total_history_units=int(hist.units.sum()), total_line_units=int(L.qty.sum()),
             chemists_ordering_exact=int((m2.c == m2.chemists_ordering).sum()), chemists_ordering_cells=int(len(m2)))
log("   reconciliation:", RECON)

# ============================================================================ not_available_log
log("[6] not_available_log ...")
na_rows = []
sub_i = L.index[L.short_q > 0]
for i in sub_i:
    r = L.loc[i]
    na_rows.append(dict(date=r.date.strftime("%Y-%m-%d"), chemist_id=r.chemist_id, pin=r.pin, sku_id=r.sku_id,
                        qty_wanted=int(r.qty), qty_short=int(r.short_q), reason=r.reason or "out_of_stock",
                        order_id=r.order_id, source="order_line"))
# phone/counter requests that never became an order line (lost sales told to the salesman)
cellU = hist[hist.units > 0]
ev_pin_days = {}
for ev in EVENTS.values():
    for p in ev["pins"]:
        for d in DATES:
            if d >= ev["start"]:
                ev_pin_days[(p, d, ev["group"])] = 1
for r in cellU.itertuples(index=False):
    if r.group in ("chronic_bp", "chronic_diabetes", "other", "tb_watch"):
        lam = 0.004 * r.units
    else:
        lam = 0.010 * r.units
    surge_flag = ev_pin_days.get((int(r.pin), r.date, r.group), 0)
    if surge_flag:
        lam *= 4.5
    if (int(r.pin), r.group) == (400086, "diarrhoea") and r.date in DECOY_DATES:
        lam *= 0.2
    k = rng.poisson(min(lam, 40))
    for _ in range(k):
        cands = sku_by_group[r.group]
        cw = np.array([sku_pop[SIDX[s]] for s in cands])
        if surge_flag and r.group == "diarrhoea":
            cw = cw * np.array([6.0 if s in ("SKU0021", "SKU0022", "SKU0036") else 1.0 for s in cands])
        if surge_flag and r.group == "fever":
            cw = cw * np.array([4.0 if CAT_MOLECULE[s] == "Paracetamol" else 1.0 for s in cands])
        sk = cands[int(rng.choice(len(cands), p=cw / cw.sum()))]
        c = served_by_pin[int(r.pin)][int(rng.integers(len(served_by_pin[int(r.pin)])))]
        why = rng.choice(["out_of_stock", "supplier_delay", "scheme_stock_only", "pack_not_stocked", "short_supply"],
                         p=[0.55, 0.17, 0.10, 0.10, 0.08])
        q = int(min(60, 1 + rng.geometric(0.15)))
        na_rows.append(dict(date=r.date.strftime("%Y-%m-%d"), chemist_id=c, pin=int(r.pin), sku_id=sk, qty_wanted=q,
                            qty_short=q, reason=str(why), order_id="", source="phone_or_counter_request"))
na = pd.DataFrame(na_rows).sort_values(["date", "chemist_id"]).reset_index(drop=True)
na.to_csv(OUT / "not_available_log.csv", index=False)

# ============================================================================ batches
log("[7] batches, claims ...")
closing_end = stock_df[stock_df.date == AS_OF].set_index("sku_id").closing.to_dict()
SHELF = {"tablet": 36, "syrup": 24, "sachet": 24, "inhaler": 24, "respule": 24, "drops": 24, "cream": 24, "injection": 24}
batch_rows = []
bn_used = set()


def new_batch_no(s, mfg):
    for _ in range(50):
        b = f"{CAT_BRAND[s][:2].upper().replace(' ', 'X')}{mfg:%y}{chr(65 + int(rng.integers(0, 12)))}{int(rng.integers(100, 999))}"
        if (s, b) not in bn_used:
            bn_used.add((s, b))
            return b
    raise RuntimeError


def add_batch(s, mfg, exp, qty):
    b = new_batch_no(s, mfg)
    batch_rows.append(dict(sku_id=s, batch_no=b, mfg=mfg.strftime("%Y-%m"), expiry=exp.strftime("%Y-%m"),
                           expiry_date=exp.strftime("%Y-%m-%d"), qty=int(qty)))
    return b


near_skus = set(rng.choice(SKUS, 20, replace=False))
for s in SKUS:
    shelf = SHELF.get(CAT_FORM[s], 24)
    cl_q = int(closing_end[s])
    nb = int(rng.integers(2, 5)) if cl_q > 40 else 1
    if cl_q > 0:
        cuts = np.sort(rng.dirichlet(np.ones(nb) * 2.0))
        qs = np.maximum(0, np.round(cuts * cl_q)).astype(int)
        qs[-1] = cl_q - qs[:-1].sum()
    else:
        qs = np.zeros(1, dtype=int)
    for j, q in enumerate(qs):
        if s in near_skus and j == 0 and cl_q > 0:
            exp = AS_OF + pd.Timedelta(days=int(rng.integers(20, 110)))
        else:
            exp = AS_OF + pd.Timedelta(days=int(rng.integers(200, shelf * 30 - 60)))
        mfg = exp - pd.DateOffset(months=shelf)
        mfg = mfg + pd.Timedelta(days=int(rng.integers(0, 20)))
        add_batch(s, pd.Timestamp(mfg), pd.Timestamp(exp), q)
B = pd.DataFrame(batch_rows)

# claims
n_claims = 900
form_of = cat["form"].to_dict()
chem_idx = np.arange(n_ch)
cw_claim = size_w / size_w.sum()
claims = []
extra_batches = []
reject_reasons = {"expiry": ["outside_return_window", "batch_not_supplied_by_us", "zero_value_claim_not_allowed"],
                  "leakage": ["cut_strip_or_seal_broken", "photo_evidence_missing", "batch_not_supplied_by_us"],
                  "breakage": ["photo_evidence_missing", "damage_after_delivery", "batch_not_supplied_by_us"]}
for i in range(n_claims):
    typ = str(rng.choice(["expiry", "leakage", "breakage"], p=[0.46, 0.37, 0.17]))
    ci = int(rng.choice(chem_idx, p=cw_claim))
    raised = pd.Timestamp("2026-06-01") + pd.Timedelta(days=int(rng.integers(0, (pd.Timestamp("2026-11-17") - pd.Timestamp("2026-06-01")).days + 1)))
    if typ == "expiry":
        pool = [s for s in SKUS if form_of[s] in ("tablet", "sachet", "inhaler", "cream")]
    else:
        pool = [s for s in SKUS if form_of[s] in ("syrup", "drops", "injection", "respule", "inhaler")]
    pw = np.array([sku_pop[SIDX[s]] * pref[ci, SIDX[s]] for s in pool])
    s = pool[int(rng.choice(len(pool), p=pw / pw.sum()))]
    shelf = SHELF.get(form_of[s], 24)
    if typ == "expiry":
        days_after_exp = int(rng.choice([-30, -10, 0, 5, 12, 20, 35, 60, 100], p=[0.1, 0.12, 0.14, 0.14, 0.14, 0.12, 0.1, 0.08, 0.06]))
        exp = raised - pd.Timedelta(days=days_after_exp)
        mfg = exp - pd.DateOffset(months=shelf)
        bno = add_batch(s, pd.Timestamp(mfg) + pd.Timedelta(days=int(rng.integers(0, 20))), exp, 0)
        qty = int(min(80, 3 + rng.geometric(0.09)))
        late_days = max(0, days_after_exp)
    else:
        exp = raised + pd.Timedelta(days=int(rng.integers(120, 700)))
        mfg = exp - pd.DateOffset(months=shelf)
        bno = add_batch(s, pd.Timestamp(mfg) + pd.Timedelta(days=int(rng.integers(0, 20))), exp, 0)
        qty = int(min(24, 1 + rng.geometric(0.35)))
        late_days = 0
    value = round(qty * PTR[s], 2)
    # outcome
    prej = {"expiry": 0.18, "leakage": 0.13, "breakage": 0.11}[typ] + (0.35 if late_days > 30 else 0)
    horizon = (AS_OF - raised).days
    u = rng.random()
    row = dict(claim_id=f"CLM{i + 1:04d}", chemist_id=chem.chemist_id[ci], sku_id=s, batch_no=bno, type=typ, qty=qty,
               value_rs=value, raised_on=raised.strftime("%Y-%m-%d"), credit_note_on="", status="", days_to_credit="",
               credited_value_rs="", reject_reason="", decided_on="", age_days=horizon)
    if u < prej:
        dd = int(np.clip(rng.lognormal(np.log(40), 0.5), 12, 120))
        if dd <= horizon:
            row.update(status="rejected", reject_reason=str(rng.choice(reject_reasons[typ])),
                       decided_on=(raised + pd.Timedelta(days=dd)).strftime("%Y-%m-%d"))
        else:
            row.update(status="pending")
    else:
        dc = int(np.clip(rng.lognormal(np.log(88), 0.42), 30, 185))
        if dc <= horizon:
            part = rng.random() < 0.09
            cv = round(value * (rng.uniform(0.5, 0.85) if part else 1.0), 2)
            row.update(status="partially_credited" if part else "credited",
                       credit_note_on=(raised + pd.Timedelta(days=dc)).strftime("%Y-%m-%d"), days_to_credit=dc,
                       credited_value_rs=cv)
        else:
            row.update(status="pending")
    claims.append(row)
B = pd.DataFrame(batch_rows)
B["days_to_expiry"] = (pd.to_datetime(B.expiry_date) - AS_OF).dt.days
B["status"] = np.where(B.qty > 0, np.where(B.days_to_expiry <= 120, "near_expiry", "in_stock"), "none_on_hand")
B.drop(columns=["expiry_date"]).to_csv(OUT / "batches.csv", index=False)
claims_df = pd.DataFrame(claims)
claims_df.to_csv(OUT / "returns_claims.csv", index=False)

# ============================================================================ ASHA
log("[8] ASHA reports ...")
BASE = dict(fever=0.055, diarrhoea=0.032, cough=0.10, breathing=0.012, rash=0.015)
asha_pin = dict(zip(asha.asha_id, asha.pin))
pin_ashas = asha.groupby("pin").asha_id.apply(list).to_dict()
asha_locs = {}
for p, aids in pin_ashas.items():
    lids = list(loc[loc.pin == p].locality_id)
    if len(aids) == 1:
        asha_locs[aids[0]] = lids
    else:
        half = len(lids) // 2
        asha_locs[aids[0]] = lids[:half]
        asha_locs[aids[1]] = lids[half:]
loc_name = dict(zip(loc.locality_id, loc.name))
WEEKLY = {"ASHA02", "ASHA08", "ASHA12"}
RELI = {a: float(rng.uniform(0.55, 0.88)) for a in asha.asha_id}
for _a in ("ASHA01", "ASHA03", "ASHA04", "ASHA05", "ASHA06", "ASHA09", "ASHA10"):  # event-pin ASHAs are the diligent ones
    RELI[_a] = float(rng.uniform(0.82, 0.93))
HOLIDAYS = {pd.Timestamp(x) for x in ("2026-11-07", "2026-11-09", "2026-11-10", "2026-10-02", "2026-10-20")}  # Diwali days, Gandhi Jayanti, Dussehra-ish


def season(t, kind):
    # monsoon tail: more fever/diarrhoea in Aug-Sep, easing into November
    days = (t - pd.Timestamp("2026-08-22")).days
    f = {"fever": 1.5, "diarrhoea": 1.6, "cough": 0.8, "breathing": 0.9, "rash": 1.3}[kind]
    return 1 + (f - 1) * max(0.0, 1 - days / 55.0) if kind in ("fever", "diarrhoea", "rash") else 1 + 0.35 * min(1, days / 80.0)


def lift_for(t, pin, locid):
    out = dict(fever=1.0, diarrhoea=1.0, cough=1.0, breathing=1.0, rash=1.0)
    for ev in EVENTS.values():
        info = ev["pins"].get(pin)
        if info:
            fr = ramp(t, ev["start"], info["asha_lag"], 3)
            hotf = 1.0 if locid.split("-")[1] in info["hot"] else 0.45
            m = 1 + (info["asha_peak"] - 1) * fr * hotf
            if ev["group"] == "diarrhoea":
                out["diarrhoea"] *= m
            else:
                out["fever"] *= m
                out["rash"] *= 1 + 0.35 * (m - 1)
    # bad air week: citywide cough/breathing, ASHA lag 2 days, plateau to 16 Nov then fades
    d = (t - pd.Timestamp("2026-11-10")).days - 2
    if d >= 0:
        v = min(1.0, (d + 1) / 3) if t <= pd.Timestamp("2026-11-17") else max(0.0, 1 - (t - pd.Timestamp("2026-11-17")).days / 3.0)
        out["cough"] *= 1 + 0.7 * v
        out["breathing"] *= 1 + 0.9 * v
    # missed-event era: modest fever bump in Dharavi in early Oct (typhoid cluster, no pharmacy signal)
    if pin == 400017 and pd.Timestamp("2026-09-30") <= t <= pd.Timestamp("2026-10-20"):
        out["fever"] *= 1.5
    # a harmless early-September micro-cluster elsewhere (noise)
    if pin == 400071 and pd.Timestamp("2026-09-03") <= t <= pd.Timestamp("2026-09-08"):
        out["diarrhoea"] *= 2.2
    return out


HI_T = {"fever": "बुखार", "diarrhoea": "दस्त और उल्टी", "cough": "खाँसी", "breathing": "साँस फूलने की शिकायत", "rash": "दाने"}
MR_T = {"fever": "ताप", "diarrhoea": "जुलाब आणि उलट्या", "cough": "खोकला", "breathing": "धाप लागणे", "rash": "पुरळ"}
EN_T = {"fever": "bukhar", "diarrhoea": "loose motion aur ulti", "cough": "khansi", "breathing": "saans ki dikkat", "rash": "daane"}


def transcript(lang, locname, hh, c, ch, ref, water, weekly):
    parts = []
    if lang == "hi":
        parts.append(f"{'इस हफ्ते' if weekly else 'आज'} {locname} में {hh} घर गई।")
        s = [f"{v} घरों में {HI_T[k]}" for k, v in c.items() if v > 0]
        parts.append(("; ".join(s) + "।") if s else "सब ठीक है, कोई खास तकलीफ नहीं।")
        if ch:
            parts.append(f"{ch} बच्चे बीमार हैं।")
        if ref:
            parts.append(f"{ref} को अस्पताल भेजा।")
        parts.append("लोग कह रहे हैं पानी गंदा आ रहा है।" if water else ("पानी साफ आ रहा है।" if rng.random() < 0.3 else ""))
    elif lang == "mr":
        parts.append(f"{'या आठवड्यात' if weekly else 'आज'} मी {locname} मध्ये {hh} घरांना भेट दिली.")
        s = [f"{v} घरांत {MR_T[k]}" for k, v in c.items() if v > 0]
        parts.append((", ".join(s) + " आहे.") if s else "सगळे ठीक आहे, काही विशेष तक्रार नाही.")
        if ch:
            parts.append(f"{ch} लहान मुले आजारी आहेत.")
        if ref:
            parts.append(f"{ref} जणांना रुग्णालयात पाठवले.")
        parts.append("नळाचे पाणी गढूळ येत आहे असे लोक सांगतात." if water else "")
    else:
        parts.append(f"{'Is hafte' if weekly else 'Aaj'} {locname} me {hh} ghar gayi.")
        s = [f"{v} ghar me {EN_T[k]}" for k, v in c.items() if v > 0]
        parts.append((", ".join(s) + ".") if s else "Sab theek hai, koi khaas problem nahi.")
        if ch:
            parts.append(f"{ch} bachche bimar hain.")
        if ref:
            parts.append(f"{ref} ko hospital bheja.")
        parts.append("Pani gandha aa raha hai." if water else "")
    return " ".join(p for p in parts if p)


def one_row(rid, t, aid, locid, weekly, days_cov):
    pin = asha_pin[aid]
    hh = int(rng.integers(55, 111)) if weekly else int(rng.integers(10, 25))
    if weekly:
        hh = int(hh)
    lf = lift_for(t, pin, locid)
    cnt = {}
    for k in BASE:
        r = BASE[k] * season(t, k) * lf[k]
        if weekly:
            r = r  # rate per household is same; weekly visits more homes
        cnt[k] = int(min(hh, rng.poisson(r * hh)))
    anysym = cnt["diarrhoea"] + cnt["fever"] + cnt["rash"]
    sick_hh = max(cnt.values()) if cnt else 0
    ch = int(min(sick_hh * 2, rng.binomial(max(1, anysym + cnt["cough"] // 2), 0.55))) if anysym or cnt["cough"] else 0
    ref = int(rng.binomial(max(0, ch + (cnt["breathing"])), 0.22))
    water_p = 0.04 + (0.65 if lf["diarrhoea"] > 2.5 else 0.0) + (0.10 if lf["fever"] > 2.5 else 0.0)
    water = bool(rng.random() < water_p)
    lang = asha.set_index("asha_id").loc[aid, "language"]
    if rng.random() < 0.18:
        lang_used = "hinglish"
    else:
        lang_used = lang
    txt = transcript("en" if lang_used == "hinglish" else lang, loc_name[locid], hh, {k: v for k, v in cnt.items()}, ch, ref, water, weekly)
    return dict(report_id=rid, date=t.strftime("%Y-%m-%d"), asha_id=aid, locality_id=locid, pin=pin,
                report_type="weekly_summary" if weekly else "daily", households_visited=hh, fever=cnt["fever"],
                diarrhoea=cnt["diarrhoea"], cough=cnt["cough"], breathing=cnt["breathing"], rash=cnt["rash"],
                children_affected=ch, referred=ref, water_issue_reported=water, language=lang_used, transcript_snippet=txt)


arows = []
rid = 1
for aid in asha.asha_id:
    lids = asha_locs[aid]
    cur = 0
    away_until = None
    for t in DATES:
        if t.dayofweek == 6:
            continue
        weekly = aid in WEEKLY
        if weekly:
            if t.dayofweek != 5:
                continue
            if rng.random() > 0.85:
                continue
            lid = lids[int(rng.integers(len(lids)))]
            arows.append(one_row(f"AR{rid:05d}", t, aid, lid, True, 6))
            rid += 1
            continue
        if away_until is not None and t <= away_until:
            continue
        if rng.random() < 0.012:
            away_until = t + pd.Timedelta(days=int(rng.integers(2, 6)))  # sick leave / training / election duty
            continue
        p = RELI[aid] * (0.45 if t in HOLIDAYS else 1.0)
        if rng.random() > p:
            continue
        lid = lids[cur % len(lids)]
        cur += 1 if rng.random() < 0.75 else 0
        arows.append(one_row(f"AR{rid:05d}", t, aid, lid, False, 1))
        rid += 1
        if rng.random() < 0.40 and len(lids) > 1:  # a second locality the same day
            lid2 = lids[(lids.index(lid) + int(rng.integers(1, len(lids)))) % len(lids)]
            arows.append(one_row(f"AR{rid:05d}", t, aid, lid2, False, 1))
            rid += 1
asha_df = pd.DataFrame(arows)
# the bad-air week raises cough only mildly, enforce non-negative integers
asha_df.to_csv(OUT / "asha_reports.csv", index=False, encoding="utf-8")
log("   asha rows:", len(asha_df))

# ============================================================================ OFFICIAL cases + lab positivity
log("[9] official cases and lab positivity ...")
weeks = pd.date_range("2026-08-17", "2026-11-30", freq="7D")  # Monday starts; the last two weeks are PROJECTED (after the data window)
BASE_RATE = {  # cases per 100k population per week (stand-in numbers)
    "acute_diarrhoeal_disease": 11.0, "fever_dengue_like": 22.0, "acute_respiratory_infection": 70.0,
    "malaria_suspected": 2.2, "jaundice_hepatitis": 1.4}
SOURCE_OF = {"acute_diarrhoeal_disease": "IDSP-like weekly report", "fever_dengue_like": "IDSP-like weekly report",
             "acute_respiratory_infection": "IDSP-like weekly report", "malaria_suspected": "IDSP-like weekly report",
             "jaundice_hepatitis": "IDSP-like weekly report"}
HOSP_FRAC = {"acute_diarrhoeal_disease": 0.10, "fever_dengue_like": 0.09, "acute_respiratory_infection": 0.04}
slow_ward = {p: int(rng.integers(0, 4)) for p in pin_pop}  # some wards file late


def seas_off(w, syn):
    days = (w - pd.Timestamp("2026-08-17")).days
    if syn in ("fever_dengue_like", "malaria_suspected"):
        return 1.35 - 0.5 * min(1.0, days / 85.0)
    if syn == "acute_diarrhoeal_disease":
        return 1.3 - 0.3 * min(1.0, days / 85.0)
    if syn == "acute_respiratory_infection":
        return 0.9 + 0.25 * min(1.0, days / 85.0)
    return 1.0


def week_mult(w, pin, syn):
    """Average of the daily multiplier over the 7 days of the week (so partial-week onsets are partial)."""
    days = pd.date_range(w, periods=7)
    vals = []
    for t in days:
        m = 1.0
        for ev in EVENTS.values():
            if ev["syndrome"] == syn and pin in ev["pins"]:
                info = ev["pins"][pin]
                m *= 1 + (info["off_peak"] - 1) * ramp(t, ev["start"], info["off_lag"], 5)
        if syn == "acute_respiratory_infection":
            d = (t - pd.Timestamp("2026-11-10")).days - 3  # bad air: small official ARI echo, below outbreak level
            if d >= 0:
                m *= 1 + 0.12 * min(1.0, (d + 1) / 3)
        if syn == "fever_dengue_like" and pin == 400017 and pd.Timestamp("2026-09-28") <= t <= pd.Timestamp("2026-10-24"):
            # missed event: enteric/typhoid cluster presenting as fever, peaks mid-Oct
            x = (t - pd.Timestamp("2026-09-28")).days
            m *= 1 + 1.9 * np.sin(np.pi * min(1.0, x / 26.0)) ** 1.2
        vals.append(m)
    return float(np.mean(vals))


off_rows = []
for w in weeks:
    wk_end = w + pd.Timedelta(days=6)
    label = f"{w.isocalendar().year}-W{w.isocalendar().week:02d}"
    for pin in pins.pin:
        pop = pin_pop[pin]
        for syn, br in BASE_RATE.items():
            mult = week_mult(w, pin, syn)
            lam = br * pop / 100000.0 * seas_off(w, syn) * mult * rng.gamma(100, 1 / 100)
            cases = int(rng.poisson(lam))
            lag = int(rng.choice([3, 4, 5, 6]) + slow_ward[pin])
            off_rows.append(dict(week=label, week_start=w.strftime("%Y-%m-%d"), week_end=wk_end.strftime("%Y-%m-%d"), pin=pin,
                                 syndrome=syn, cases_reported=cases, source_type=SOURCE_OF[syn], report_lag_days=lag,
                                 report_date=(wk_end + pd.Timedelta(days=lag)).strftime("%Y-%m-%d"), tests_done=""))
            if syn in HOSP_FRAC:
                hc = int(rng.poisson(lam * HOSP_FRAC[syn] * rng.uniform(0.8, 1.2) * (1.0 if mult < 1.3 else 1.15)))
                hl = int(rng.integers(7, 15))
                off_rows.append(dict(week=label, week_start=w.strftime("%Y-%m-%d"), week_end=wk_end.strftime("%Y-%m-%d"),
                                     pin=pin, syndrome=syn, cases_reported=hc, source_type="hospital admissions",
                                     report_lag_days=hl, report_date=(wk_end + pd.Timedelta(days=hl)).strftime("%Y-%m-%d"),
                                     tests_done=""))

# lab positivity (fictional lab partner) + official 'lab positivity' rows
LAB_BASE = {"dengue_ns1": 0.095, "typhoid": 0.060, "malaria": 0.016}
LAB_SYN = {"dengue_ns1": "fever_dengue_like", "typhoid": "fever_dengue_like", "malaria": "malaria_suspected"}
lab_rows = []
for w in weeks:
    wk_end = w + pd.Timedelta(days=6)
    label = f"{w.isocalendar().year}-W{w.isocalendar().week:02d}"
    for pin in pins.pin:
        pop = pin_pop[pin]
        for test, p0 in LAB_BASE.items():
            tests = int(rng.poisson({"dengue_ns1": 70, "typhoid": 50, "malaria": 45}[test] * pop / 200000.0 * rng.uniform(0.8, 1.2)))
            days = (w - pd.Timestamp("2026-08-17")).days
            if test == "dengue_ns1":
                p = p0 * (1.25 - 0.45 * min(1.0, days / 85.0))
                mm = week_mult(w, pin, "fever_dengue_like")
                if pin in (400088, 400043):
                    p = min(0.5, p * (1 + 0.9 * (mm - 1)))
                if pin == 400017:
                    mm = 1.0
            elif test == "typhoid":
                p = p0
                if pin == 400017 and pd.Timestamp("2026-09-28") <= w <= pd.Timestamp("2026-10-26"):
                    p = p0 * (1 + 2.2 * np.sin(np.pi * min(1.0, ((w + pd.Timedelta(days=3)) - pd.Timestamp("2026-09-28")).days / 26.0)))
            else:
                p = p0 * (1.2 - 0.4 * min(1.0, days / 85.0))
            pos = int(rng.binomial(tests, min(0.95, p))) if tests else 0
            lag = int(rng.integers(3, 8))
            lab_rows.append(dict(week=label, week_start=w.strftime("%Y-%m-%d"), pin=pin, test=test, tests_done=tests,
                                 positives=pos, positivity_pct=round(100.0 * pos / tests, 1) if tests else "",
                                 lab_id="LAB01", report_date=(wk_end + pd.Timedelta(days=lag)).strftime("%Y-%m-%d"),
                                 data_status="observed_sim" if wk_end + pd.Timedelta(days=lag) <= AS_OF else "projected_sim"))
lab_df = pd.DataFrame(lab_rows)
lab_df.to_csv(OUT / "lab_positivity.csv", index=False)
# the official file also carries lab confirmation rows (state/municipal lab network, separate from LAB01)
for r in lab_df.itertuples(index=False):
    w = pd.Timestamp(r.week_start)
    wk_end = w + pd.Timedelta(days=6)
    off_t = int(max(0, rng.poisson(r.positives * rng.uniform(1.4, 2.4))))
    tests_off = int(r.tests_done * rng.uniform(1.4, 2.4)) if r.tests_done else 0
    lag = int(rng.integers(5, 11))
    off_rows.append(dict(week=r.week, week_start=r.week_start, week_end=wk_end.strftime("%Y-%m-%d"), pin=r.pin,
                         syndrome={"dengue_ns1": "dengue_lab_confirmed", "typhoid": "typhoid_lab_confirmed", "malaria": "malaria_lab_confirmed"}[r.test],
                         cases_reported=off_t, source_type="lab positivity", report_lag_days=lag,
                         report_date=(wk_end + pd.Timedelta(days=lag)).strftime("%Y-%m-%d"), tests_done=tests_off))
off = pd.DataFrame(off_rows)
off["data_status"] = np.where(pd.to_datetime(off.report_date) <= AS_OF, "observed_sim", "projected_sim")
off = off.sort_values(["week_start", "pin", "source_type", "syndrome"]).reset_index(drop=True)
off.to_csv(OUT / "official_cases.csv", index=False)

# ============================================================================ environment (REAL where possible)
log("[10] environment ...")
POINTS = {"P1_Kurla": (19.07, 72.88), "P2_Mankhurd_Govandi": (19.05, 72.925), "P3_Bandra": (19.06, 72.83), "P4_Andheri": (19.115, 72.87)}


def fetch(url):
    with urllib.request.urlopen(url, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def get_env(refresh=False):
    out = {}
    for pid, (la, lo) in POINTS.items():
        cf = CACHE / f"open_meteo_{pid}.json"
        if cf.exists() and not refresh:
            out[pid] = json.load(open(cf))
            continue
        try:
            w = fetch("https://archive-api.open-meteo.com/v1/archive?latitude=%s&longitude=%s&start_date=2026-08-22&end_date=2026-11-19"
                      "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean&timezone=Asia%%2FKolkata" % (la, lo))
            a = fetch("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=%s&longitude=%s&start_date=2026-08-22&end_date=2026-11-19"
                      "&hourly=pm2_5,pm10&timezone=Asia%%2FKolkata" % (la, lo))
            out[pid] = dict(weather=w, air=a)
            json.dump(out[pid], open(cf, "w"))
        except Exception as e:  # noqa
            log("   open-meteo failed for", pid, e)
            out[pid] = None
    return out


envraw = get_env("--refresh-weather" in sys.argv)
env_pt = {}
for pid, raw in envraw.items():
    if raw is None:
        continue
    try:
        wd = pd.DataFrame(raw["weather"]["daily"])
        wd["date"] = pd.to_datetime(wd.pop("time"))
        ah = pd.DataFrame(raw["air"]["hourly"])
        ah["date"] = pd.to_datetime(ah.pop("time")).dt.normalize()
        ad = ah.groupby("date").agg(pm2_5=("pm2_5", "mean"), pm10=("pm10", "mean")).reset_index()
        env_pt[pid] = wd.merge(ad, on="date", how="left")
    except Exception as e:  # noqa
        log("   parse failed", pid, e)
env_rows = []
pin_point = {}
for r in pins.itertuples():
    best = min(POINTS, key=lambda k: (POINTS[k][0] - r.lat) ** 2 + (POINTS[k][1] - r.lng) ** 2)
    pin_point[r.pin] = best
sim_used = False
for r in pins.itertuples():
    pid = pin_point[r.pin]
    df = env_pt.get(pid)
    for d in DATES:
        if df is not None and (df.date == d).any():
            x = df[df.date == d].iloc[0]
            if pd.notna(x.pm2_5) and pd.notna(x.temperature_2m_max):
                env_rows.append(dict(date=d.strftime("%Y-%m-%d"), pin=r.pin, station_point=pid,
                                     temp_max_c=round(x.temperature_2m_max, 1), temp_min_c=round(x.temperature_2m_min, 1),
                                     precip_mm=round(x.precipitation_sum, 1), humidity_pct=round(x.relative_humidity_2m_mean, 0),
                                     pm2_5=round(x.pm2_5, 1), pm10=round(x.pm10, 1), source="open-meteo"))
                continue
        sim_used = True
        days = (d - pd.Timestamp("2026-08-22")).days
        env_rows.append(dict(date=d.strftime("%Y-%m-%d"), pin=r.pin, station_point=pid,
                             temp_max_c=round(31 - 0.01 * days + rng.normal(0, 1), 1), temp_min_c=round(26 - 0.07 * days / 5 + rng.normal(0, 1), 1),
                             precip_mm=round(max(0, rng.gamma(0.4, 12) - 2) * max(0, 1 - days / 70), 1),
                             humidity_pct=round(float(np.clip(80 - days * 0.2 + rng.normal(0, 5), 30, 99)), 0),
                             pm2_5=round(30 + days * 0.5 + rng.normal(0, 8), 1), pm10=round(60 + days * 0.8 + rng.normal(0, 14), 1),
                             source="simulated"))
env = pd.DataFrame(env_rows)
env.to_csv(OUT / "environment_daily.csv", index=False)
log("   env rows:", len(env), "sources:", env.source.value_counts().to_dict())

# ============================================================================ BACKTEST
log("[11] back-test ...")
ACUTE = ["fever", "diarrhoea", "respiratory", "allergy"]  # heat/eye/fungal/tb_watch are too sparse for a stable signal
daily_c = L.groupby(["date", "chemist_id", "group"]).qty.sum()
ALLD = pd.DatetimeIndex(DATES)
zero_ser = pd.Series(0, index=ALLD)
CD = {k: v.reindex(ALLD, fill_value=0) for k, v in {kk: daily_c.xs(kk, level=(1, 2)) for kk in set(zip(daily_c.index.get_level_values(1), daily_c.index.get_level_values(2)))}.items()}


def pharmacy_alerts(pin, grp):
    ser = hist[(hist.pin == pin) & (hist.group == grp)].set_index("date").units.reindex(ALLD, fill_value=0)
    w7 = ser.rolling(7).sum()
    base = w7.shift(7).rolling(28).median()
    ratio = w7 / base
    # breadth: share of active chemists whose own 7d total exceeds 1.3x their own trailing baseline
    ids = served_by_pin[pin]
    cw = pd.DataFrame({c: CD.get((c, grp), zero_ser) for c in ids})
    c7 = cw.rolling(7).sum()
    cbase = c7.shift(7).rolling(28).median()
    above = (c7 > 1.6 * cbase.clip(lower=3)) & (c7 >= 4)
    active = ((c7 > 0) | (cbase > 0))
    breadth = above.sum(axis=1) / active.sum(axis=1).replace(0, np.nan)
    fire = (ratio > 1.5) & (breadth > 0.40) & (w7 >= 60) & (base >= 25)
    return ratio, breadth, fire, w7


alert_table = {}
for pin in pins.pin:
    for g in ACUTE:
        ratio, breadth, fire, w7 = pharmacy_alerts(int(pin), g)
        alert_table[(int(pin), g)] = (ratio, breadth, fire)


def first_true(s, after=None):
    s = s[s]
    if after is not None:
        s = s[s.index >= after]
    return None if s.empty else s.index[0]


# ASHA rise: 3-report rolling household rate for symptom vs the pin's prior-28-day median
def asha_rise(pin, kinds, start):
    d = asha_df[asha_df.pin == pin].copy()
    d["date"] = pd.to_datetime(d.date)
    d["sym"] = d[kinds].sum(axis=1)
    daily = d.groupby("date").agg(sym=("sym", "sum"), hh=("households_visited", "sum"))
    daily = daily.reindex(ALLD).fillna(0)
    sym3, hh3 = daily.sym.rolling(4, min_periods=1).sum(), daily.hh.rolling(4, min_periods=1).sum()
    rate = (sym3 / hh3.replace(0, np.nan))
    base_rate = (daily.sym.rolling(28).sum() / daily.hh.rolling(28).sum().replace(0, np.nan)).shift(5)
    fire = (rate > 2.5 * base_rate) & (sym3 >= 5)
    return first_true(fire, start - pd.Timedelta(days=2))


def off_rise(pin, syn, src="IDSP-like weekly report"):
    d = off[(off.pin == pin) & (off.syndrome == syn) & (off.source_type == src)].sort_values("week_start")
    d = d.reset_index(drop=True)
    for i in range(6, len(d)):
        base = float(d.cases_reported[max(0, i - 6):i].median())
        c = d.cases_reported[i]
        if c >= max(1.6 * base, base + 4 * np.sqrt(max(base, 1))):
            return d.loc[i]
    return None


summary = dict(generated_for="FirstSign back-test on SIMULATED data", as_of=str(AS_OF.date()),
               rule="pharmacy alert = 7-day units / median of the 28 preceding 7-day windows > 1.5 AND breadth > 40% "
                    "(share of the pin's active chemists whose own 7-day units exceed 1.6x their own baseline) "
                    "AND volume floor (7-day units >= 60, baseline >= 25). Evaluated daily for fever, diarrhoea, respiratory, allergy.",
               asha_rule="rolling 4-day households with the symptom per household visited > 2.5x the pin's prior 28-day rate and >= 5 households",
               official_rule="first weekly IDSP-like count >= max(1.6 x median of previous 6 weeks, median + 4 x sqrt(median))",
               caveat="Official counts for weeks reported after 2026-11-19 (and the weeks starting 23 and 30 Nov) are PROJECTED simulated values (report_date after 2026-11-19); "
                      "the back-test for the two live events is therefore a replay of a simulated scenario, not an observed result. "
                      "Real literature leads: none to ~2 weeks, weakest for antidiarrhoeals (see research_day1/R5).",
               events=[])


def event_block(key, ev):
    grp, syn = ev["group"], ev["syndrome"]
    per = []
    for pin, info in ev["pins"].items():
        ratio, breadth, fire = alert_table[(pin, grp)]
        a_date = first_true(fire, ev["start"] - pd.Timedelta(days=3))
        kinds = ["diarrhoea"] if grp == "diarrhoea" else ["fever"]
        as_d = asha_rise(pin, kinds, ev["start"])
        orow = off_rise(pin, syn)
        o_week = None if orow is None else orow.week_start
        o_rep = None if orow is None else orow.report_date
        rec = dict(pin=int(pin), area=pins.set_index("pin").loc[pin, "area"],
                   pharmacy_alert_date=None if a_date is None else str(a_date.date()),
                   pharmacy_peak_ratio=round(float(ratio.loc[ev["start"]:].max()), 2),
                   asha_rise_date=None if as_d is None else str(as_d.date()),
                   official_first_elevated_week_start=o_week, official_report_date=o_rep,
                   official_projected=None if o_rep is None else bool(pd.Timestamp(o_rep) > AS_OF))
        if a_date is not None and as_d is not None:
            rec["lead_vs_asha_days"] = int((as_d - a_date).days)
        if a_date is not None and o_week is not None:
            rec["lead_vs_official_week_start_days"] = int((pd.Timestamp(o_week) - a_date).days)
            rec["lead_vs_official_report_date_days"] = int((pd.Timestamp(o_rep) - a_date).days)
        per.append(rec)
    dates = [r["pharmacy_alert_date"] for r in per if r["pharmacy_alert_date"]]
    first = min(dates) if dates else None
    return dict(event=key, group=grp, syndrome=syn, pharmacy_story_start=str(ev["start"].date()),
                first_pharmacy_alert_date=first, per_pin=per)


for k, ev in EVENTS.items():
    summary["events"].append(event_block(k, ev))

# decoy
ratio, breadth, fire = alert_table[(400086, "diarrhoea")]
dec_days = sorted(DECOY_DATES)
summary["decoy_ors_scheme"] = dict(pin=400086, chemist=DECOY_CHEMIST, scheme_id="SCH001",
    peak_7d_ratio=round(float(ratio.loc["2026-11-10":].max()), 2),
    peak_breadth=round(float(breadth.loc["2026-11-10":].max()), 2),
    alert_fired=bool(fire.loc["2026-11-10":].any()),
    note="High volume, low breadth: the rule must NOT alert. alert_fired=false is the desired outcome.")

# false alarm: respiratory (bad air) alerts with no official outbreak and no sustained ASHA signal
fa = []
for pin in pins.pin:
    ratio, breadth, fire = alert_table[(int(pin), "respiratory")]
    d0 = first_true(fire, pd.Timestamp("2026-11-08"))
    if d0 is not None:
        orow = off_rise(int(pin), "acute_respiratory_infection")
        fa.append(dict(pin=int(pin), alert_date=str(d0.date()), official_elevated=orow is not None,
                       asha_cough_rise_date=(lambda x: None if x is None else str(x.date()))(asha_rise(int(pin), ["cough", "breathing"], pd.Timestamp("2026-11-08")))))
summary["false_alarm"] = dict(group="respiratory", cause="citywide bad-air week (PM2.5 rise), not an infectious outbreak",
    pins_alerting=fa, verdict="Pharmacy rule fired in pins listed; official ARI counts stay within normal range and ASHA cough bump is mild and short. "
    "The app should show 'region-wide, discounted' rather than an outbreak.")
# any other pharmacy alerts outside the stories
oth = []
for (pin, g), (ratio, breadth, fire) in alert_table.items():
    if fire.any():
        d0 = fire[fire].index[0]
        story = ((g == "diarrhoea" and pin in EVENTS["E1_diarrhoea_waterborne"]["pins"]) or (g == "fever" and pin in EVENTS["E2_dengue_like_fever"]["pins"]) or g == "respiratory")
        if not story:
            oth.append(dict(pin=pin, group=g, first_alert=str(d0.date()), days_alerting=int(fire.sum())))
summary["other_pharmacy_alerts_outside_stories"] = oth

# missed event
ratio, breadth, fire = alert_table[(400017, "fever")]
win = slice("2026-09-20", "2026-11-05")
orow = off_rise(400017, "fever_dengue_like")
lab = lab_df[(lab_df.pin == 400017) & (lab_df.test == "typhoid")].set_index("week_start").positivity_pct
summary["missed_event"] = dict(event="Typhoid / enteric fever cluster, Dharavi 400017", official_first_elevated_week_start=None if orow is None else orow.week_start,
    official_report_date=None if orow is None else orow.report_date,
    peak_typhoid_lab_positivity_pct=float(pd.to_numeric(lab.loc["2026-09-21":"2026-11-02"], errors="coerce").max()),
    pharmacy_fever_peak_ratio_in_window=round(float(ratio.loc[win].max()), 2),
    pharmacy_alert_fired=bool(fire.loc[win].any()),
    why_missed="Typhoid is treated on prescription antibiotics from clinics and labs; OTC fever and diarrhoea volumes barely move, so the pharmacy signal stays under threshold.")
# lead statistics
leads = [r["lead_vs_official_report_date_days"] for e in summary["events"] for r in e["per_pin"] if "lead_vs_official_report_date_days" in r]
leadsw = [r["lead_vs_official_week_start_days"] for e in summary["events"] for r in e["per_pin"] if "lead_vs_official_week_start_days" in r]
lasha = [r["lead_vs_asha_days"] for e in summary["events"] for r in e["per_pin"] if "lead_vs_asha_days" in r]
summary["lead_stats"] = dict(lead_vs_asha_days=lasha, lead_vs_official_week_start_days=leadsw, lead_vs_official_report_date_days=leads,
    median_lead_vs_official_report_date=None if not leads else float(np.median(leads)),
    median_lead_vs_asha=None if not lasha else float(np.median(lasha)))
summary["reconciliation"] = RECON
json.dump(summary, open(OUT / "backtest_summary.json", "w", encoding="utf-8"), indent=2, default=str)

# ---- counts
for f in sorted(OUT.glob("*.csv")):
    log(f"   {f.name:28s} {sum(1 for _ in open(f, encoding='utf-8')) - 1:>8d} rows")
log("done.")
