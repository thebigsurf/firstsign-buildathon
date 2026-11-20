"""Validate data/extended/: joins, ranges, reconciliation with history.csv, row counts.

Usage: python data/tools/validate_extended.py      (exit 1 on any failure)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
E = ROOT / "extended"
err: list[str] = []


def check(c, m):
    if not c:
        err.append(m)


def rd(n, **k):
    return pd.read_csv(E / n, **k)


cat = pd.read_csv(ROOT / "catalogue.csv")
hist = pd.read_csv(ROOT / "history.csv", parse_dates=["date"])
chem = pd.read_csv(ROOT / "chemists.csv")
dist = json.load(open(ROOT / "distributor.json", encoding="utf-8"))
pins = pd.read_csv(ROOT / "pincodes.csv")
asha = pd.read_csv(ROOT / "asha.csv")
loc = pd.read_csv(ROOT / "localities.csv")
served = set(dist["chemist_ids"])
SK = set(cat.sku_id)
PINS = set(pins.pin)

orders = rd("orders.csv")
lines = rd("order_lines.csv", keep_default_na=False)
na = rd("not_available_log.csv", keep_default_na=False)
stock = rd("distributor_stock.csv")
batches = rd("batches.csv")
claims = rd("returns_claims.csv", keep_default_na=False)
schemes = rd("schemes.csv", keep_default_na=False)
staff = rd("salesmen.csv", keep_default_na=False)
ar = rd("asha_reports.csv")
off = rd("official_cases.csv", keep_default_na=False)
env = rd("environment_daily.csv")
lab = rd("lab_positivity.csv", keep_default_na=False)
prices = rd("sku_prices.csv")
bt = json.load(open(E / "backtest_summary.json", encoding="utf-8"))

# ---- keys
check(orders.order_id.is_unique, "order_id not unique")
check(lines.set_index(["order_id", "line_no"]).index.is_unique, "(order_id,line_no) not unique")
check(set(lines.order_id) <= set(orders.order_id), "order_lines -> orders FK")
check(set(orders.order_id) <= set(lines.order_id), "orders without lines")
check(set(orders.chemist_id) <= served, "orders.chemist_id not in distributor chemists")
cp = chem.set_index("chemist_id").pin
check((orders.chemist_id.map(cp) == orders.pin).all(), "orders.pin != chemist pin")
check(set(orders.pin) <= PINS, "orders.pin FK")
sm = set(staff[staff.role == "salesman"].salesman_id)
cl = set(staff[staff.role == "order_clerk"].first_name)
check(set(orders.salesman_id) <= sm, "orders.salesman_id FK")
check(set(orders.approved_by) <= cl, "orders.approved_by not a clerk")
check(set(lines.sku_id) <= SK, "lines.sku_id FK")
check(set(lines.substituted_sku_id) - {""} <= SK, "substituted_sku_id FK")
check(set(lines.scheme_applied) - {""} <= set(schemes.scheme_id), "scheme_applied FK")
check(set(orders.channel) <= {"voice_note", "photo", "whatsapp_text", "salesman", "phone_call", "app"}, "channel values")
check(set(lines.line_status) <= {"supplied", "short", "substituted", "not_available"}, "line_status values")
check((lines.qty >= 1).all(), "qty >= 1")
check((lines.qty_supplied >= 0).all() and (lines.qty_supplied <= lines.qty).all(), "qty_supplied range")
sub = lines[lines.line_status == "substituted"]
check((sub.substituted_sku_id != "").all(), "substituted lines need substituted_sku_id")
check((lines[lines.line_status != "substituted"].substituted_sku_id == "").all(), "stray substituted_sku_id")
check((lines.raw_text.str.len() > 0).all(), "empty raw_text")
ts = pd.to_datetime(orders.received_at.str[:19])
check(ts.min() >= pd.Timestamp("2026-08-22") and ts.max() < pd.Timestamp("2026-11-20"), "received_at window")
hr = ts.dt.hour + ts.dt.minute / 60
check(((hr >= 20) & (hr < 24)).mean() > 0.25, "evening batch share looks too low")
check(orders.clerk_minutes_estimate.between(0, 60).all(), "clerk_minutes range")
# channel mix by chemist software
m = orders.merge(chem[["chemist_id", "software"]], on="chemist_id")
paper = m[m.software == "paper"].channel
check(paper.isin(["voice_note", "photo", "salesman", "phone_call", "whatsapp_text"]).all() and (paper == "app").sum() == 0,
      "paper shops should not use app")

# ---- reconciliation
ln = lines.merge(orders[["order_id", "received_at", "pin"]], on="order_id")
ln["date"] = pd.to_datetime(ln.received_at.str[:10])
ln["group"] = ln.sku_id.map(cat.set_index("sku_id").group)
rec = ln.groupby(["date", "pin", "group"]).qty.sum().rename("u").reset_index()
mm = hist.merge(rec, on=["date", "pin", "group"], how="outer").fillna(0)
d = (mm.units - mm.u).abs()
print(f"RECONCILIATION  cells={len(mm)}  exact={(d == 0).sum()}  max_abs_diff={int(d.max())}  "
      f"history_units={int(hist.units.sum())}  line_units={int(lines.qty.sum())}")
check(d.max() <= 0, "line totals do not reconcile with history.csv")
cc = ln.merge(orders[["order_id", "chemist_id"]], on="order_id").groupby(["date", "pin", "group"]).chemist_id.nunique().rename("c").reset_index()
m3 = hist.merge(cc, on=["date", "pin", "group"], how="left").fillna({"c": 0})
check((m3.c == m3.chemists_ordering).all(), "chemists_ordering mismatch")

# ---- not available
check(set(na.sku_id) <= SK and set(na.chemist_id) <= served and set(na.pin) <= PINS, "na_log FK")
check(set(na.order_id) - {""} <= set(orders.order_id), "na_log order FK")
check((na.qty_short.astype(int) <= na.qty_wanted.astype(int)).all(), "na qty_short <= wanted")

# ---- stock
check(set(stock.sku_id) == SK, "stock covers all SKUs")
check(len(stock) == len(SK) * 90, "stock rows != skus*90")
check(((stock.opening + stock.received - stock.dispatched) == stock.closing).all(), "stock identity opening+received-dispatched=closing")
check((stock.closing >= 0).all(), "negative stock")
disp = lines.merge(orders[["order_id", "received_at"]], on="order_id")
last = stock[stock.date == "2026-11-19"].set_index("sku_id").closing
bsum = batches.groupby("sku_id").qty.sum()
check(((bsum.reindex(last.index).fillna(0)) == last).all(), "batch qty sum != closing stock on 2026-11-19")
check(set(batches.sku_id) <= SK, "batches FK")
check(batches.set_index(["sku_id", "batch_no"]).index.is_unique, "batch key unique")
check((batches.qty >= 0).all(), "batch qty")

# ---- claims
check(set(claims.chemist_id) <= served and set(claims.sku_id) <= SK, "claims FK")
bk = set(zip(batches.sku_id, batches.batch_no))
check(all(k in bk for k in zip(claims.sku_id, claims.batch_no)), "claims batch FK")
check(claims.status.isin(["credited", "partially_credited", "pending", "rejected"]).all(), "claim status")
cr = claims[claims.credit_note_on != ""]
dd = cr.days_to_credit.astype(int)
check(dd.between(30, 190).all(), "days_to_credit range")
check((pd.to_datetime(cr.credit_note_on) <= pd.Timestamp("2026-11-19")).all(), "credit note after as-of")
check(set(claims.type) <= {"expiry", "leakage", "breakage"}, "claim type")
print("claims status:", claims.status.value_counts().to_dict(), " median days_to_credit:", int(dd.median()))

# ---- schemes
check(all(set(s.split("|")) <= SK for s in schemes.sku_ids), "scheme sku FK")
check(all(e == "ALL" or set(e.split("|")) <= served for e in schemes.eligible_chemists), "scheme eligible FK")
ors = schemes[schemes.scheme_id == "SCH001"].iloc[0]
check(ors.start == "2026-11-12", "ORS scheme dates")

# ---- ASHA
check(set(ar.asha_id) <= set(asha.asha_id), "asha FK")
check(set(ar.locality_id) <= set(loc.locality_id), "locality FK")
check((ar.locality_id.str[:6].astype(int) == ar.pin).all(), "asha locality pin")
check((ar.pin == ar.asha_id.map(asha.set_index("asha_id").pin)).all(), "asha pin")
sy = ar[["fever", "diarrhoea", "cough", "breathing", "rash"]]
check((sy.le(ar.households_visited, axis=0)).all().all() and (sy >= 0).all().all(), "asha counts <= households")
check(ar.date.min() >= "2026-08-22" and ar.date.max() <= "2026-11-19", "asha dates")
check(not ar.duplicated(["date", "asha_id", "locality_id"]).any(), "dup asha report")
print("asha reports:", len(ar), " ASHA-days missing share:", round(1 - ar.groupby("asha_id").date.nunique().sum() / (asha.shape[0] * 90), 2))

# ---- official / lab / env
check(set(off.pin.astype(int)) <= PINS and set(lab.pin) <= PINS and set(env.pin) <= PINS, "pin FKs official/lab/env")
check((off.cases_reported.astype(int) >= 0).all(), "cases >= 0")
check(off.report_lag_days.astype(int).between(1, 30).all(), "lag range")
check(set(off.source_type) == {"IDSP-like weekly report", "hospital admissions", "lab positivity"}, "source types")
check((lab.positives <= lab.tests_done).all(), "positives <= tests")
check(len(env) == 20 * 90, "env rows")
check(env.pm2_5.between(0, 600).all() and env.temp_max_c.between(15, 48).all(), "env ranges")
check(env.source.isin(["open-meteo", "simulated"]).all(), "env source")
print("env sources:", env.source.value_counts().to_dict())
check(set(prices.sku_id) == SK, "prices cover SKUs")

# ---- backtest
check(len(bt["events"]) == 2 and "false_alarm" in bt and "missed_event" in bt, "backtest sections")
check(bt["decoy_ors_scheme"]["alert_fired"] is False, "decoy must not alert")
check(bt["missed_event"]["pharmacy_alert_fired"] is False, "missed event should not alert")

print("\nrow counts")
for f in sorted(E.glob("*.csv")):
    print(f"  {f.name:26s}{sum(1 for _ in open(f, encoding='utf-8')) - 1:>8d}")
tot = sum(f.stat().st_size for f in E.rglob("*") if f.is_file())
print(f"  total size on disk: {tot / 1e6:.1f} MB")
if err:
    print("\nFAILURES:")
    for e in err:
        print(" -", e)
    sys.exit(1)
print("\nALL CHECKS PASSED")
