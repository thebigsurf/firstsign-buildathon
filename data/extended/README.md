# FirstSign extended dataset (SIMULATED fallback)

The base seed set in `data/` (catalogue, chemists, history.csv ...) is untouched. This folder adds the raw records each actor would really generate, all joined to the base IDs. Window: 2026-08-22 to 2026-11-19 (same 90 days as `history.csv`).

**Real vs simulated:** only `environment_daily.csv` is real (Open-Meteo weather and air quality, `source=open-meteo`). Everything else is simulated. The UI must keep saying "Simulated history for demo". No customer or patient names exist anywhere; workers have first names only.

## Regenerate and validate

```
python data/tools/generate_extended.py      # about 1.5 minutes, deterministic (seed 20261121), identical files on every run
python data/tools/validate_extended.py      # joins, ranges, reconciliation; exit 1 on failure
```

Open-Meteo responses are cached in `extended/_cache/` so reruns are offline and identical. Add `--refresh-weather` to refetch. If a fetch fails the generator falls back to simulated weather and marks those rows `source=simulated` (not needed in the current build: 1800/1800 rows are real).

## Files

| File | Rows | Columns | Real / simulated |
|---|---|---|---|
| `orders.csv` | 14,331 | order_id, chemist_id, pin, received_at (+05:30), channel, salesman_id, status, approved_by, clerk_minutes_estimate | simulated |
| `order_lines.csv` | 56,042 | order_id, line_no, raw_text, sku_id, qty, unit, scheme_applied, line_status, substituted_sku_id, qty_supplied, free_qty | simulated |
| `not_available_log.csv` | 6,118 | date, chemist_id, pin, sku_id, qty_wanted, qty_short, reason, order_id, source | simulated |
| `distributor_stock.csv` | 14,400 | date, sku_id, opening, received, dispatched, closing, days_of_cover, on_order | simulated |
| `batches.csv` | 1,362 | sku_id, batch_no, mfg (YYYY-MM), expiry (YYYY-MM), qty, days_to_expiry, status | simulated |
| `returns_claims.csv` | 900 | claim_id, chemist_id, sku_id, batch_no, type, qty, value_rs, raised_on, credit_note_on, status, days_to_credit, credited_value_rs, reject_reason, decided_on, age_days | simulated |
| `schemes.csv` | 22 | scheme_id, brand, sku_ids, offer, offer_type, buy_qty, free_qty, min_qty, start, end, eligible_chemists, notes | simulated |
| `salesmen.csv` | 16 | salesman_id, first_name, role (salesman / order_clerk), beat_pins, beat_days | simulated |
| `sku_prices.csv` | 160 | sku_id, mrp_rs, ptr_rs | simulated (extra, needed for claim values) |
| `asha_reports.csv` | 783 | report_id, date, asha_id, locality_id, pin, report_type (daily / weekly_summary), households_visited, fever, diarrhoea, cough, breathing, rash, children_affected, referred, water_issue_reported, language (hi / mr / hinglish), transcript_snippet | simulated |
| `official_cases.csv` | 3,520 | week, week_start, week_end, pin, syndrome, cases_reported, source_type, report_lag_days, report_date, tests_done, data_status | simulated stand-in |
| `lab_positivity.csv` | 960 | week, week_start, pin, test (dengue_ns1 / typhoid / malaria), tests_done, positives, positivity_pct, lab_id (LAB01, fictional), report_date, data_status | simulated |
| `environment_daily.csv` | 1,800 (20 pins x 90 days) | date, pin, station_point, temp_max_c, temp_min_c, precip_mm, humidity_pct, pm2_5, pm10, source | **REAL** (Open-Meteo) |
| `backtest_summary.json` | - | per-event alert dates, ASHA and official rise dates, leads, decoy, false alarm, missed event, reconciliation | computed from the files above |

Notes on columns: `line_status` is one of supplied / short / substituted / not_available. `qty` is what the chemist asked for (this is what reconciles with `history.csv`); `qty_supplied` is what went out. `data_status` is `observed_sim` when `report_date` is on or before 2026-11-19, else `projected_sim`. `approved_by` is a clerk first name from `salesmen.csv` (role order_clerk). `scheme_applied` joins to `schemes.csv`. Claim `batch_no` joins to `batches.csv` (historic batches carry qty 0, status none_on_hand).

## Reconciliation with history.csv (checked by the validator)

For every date x pin x group, the sum of `order_lines.qty` equals `history.units` **exactly**: 19,800 of 19,800 cells exact, max absolute difference 0, total 629,834 units on both sides. The number of distinct chemists per cell also equals `history.chemists_ordering` in all 19,800 cells. Method: each history cell is split across its `chemists_ordering` chemists (heavy-tailed shop size), then into 1 to 3 SKU lines per chemist, so the totals hold by construction.

## Back-test (from `backtest_summary.json`)

Rule: 7-day units / median of the 28 preceding 7-day windows > 1.5 AND breadth > 40% (share of the pin's active chemists whose own 7-day units exceed 1.6x their baseline), with a volume floor (>= 60 units in the window, baseline >= 25).

| Event | Pharmacy alert | ASHA rise | Official (IDSP-like) first elevated week, report date | Lead vs official report date |
|---|---|---|---|---|
| Diarrhoea, Sion 400022 | 16 Nov | 18 Nov (+2 d) | week of 16 Nov, 25 Nov (projected) | 9 d |
| Diarrhoea, Kurla West 400070 | 17 Nov | 19 Nov (+2 d) | week of 23 Nov, 4 Dec (projected) | 17 d |
| Diarrhoea, Kurla East 400024 | 17 Nov | not yet visible | week of 23 Nov, 5 Dec (projected) | 18 d |
| Fever, Mankhurd 400088 | 16 Nov | 16 Nov (+0 d) | week of 16 Nov, 28 Nov (projected) | 12 d |
| Fever, Govandi 400043 | 15 Nov | 17 Nov (+2 d) | week of 16 Nov, 27 Nov (projected) | 12 d |

Median lead 12 days vs the official report date, 2 days vs ASHA. Leads vary by pin on purpose (literature: none to about two weeks, weakest for antidiarrhoeals).

* **Decoy (ORS scheme, CH082, Ghatkopar West 400086):** 7-day ratio peaks at 2.91 but breadth is 0.33, so no alert fires. Desired outcome.
* **False alarm:** citywide respiratory bump in the bad-air week. The rule fires in 5 pins (400024, 400022, 400017, 400019, 400076) but official ARI counts stay normal and the ASHA cough rise is mild. The app should show "region-wide, discounted".
* **Missed event:** typhoid / enteric fever cluster in Dharavi 400017 (late Sep to Oct). Official fever counts rise from the week of 5 Oct (reported 16 Oct), typhoid lab positivity peaks at about 18%, but the pharmacy fever ratio stays at 1.28 and no alert fires. Reason: prescription-led, clinic and lab driven.
* `other_pharmacy_alerts_outside_stories` lists ten short single-pin blips in the base history (for example Bandra West diarrhoea in mid-Oct, Ghatkopar West diarrhoea on 6 Nov right after Diwali). They are noise and shown for honesty.

**Important caveat:** the base history ends 19 Nov, only 5 days after the diarrhoea story starts. Official counts for the live events therefore do not exist yet. Official rows for weeks starting 23 and 30 Nov, and every row with `report_date` after 19 Nov, are PROJECTED simulated values (`data_status=projected_sim`). The live-event back-test is a replay of a simulated scenario, not an observed result. The only fully observed (simulated) retrospective items are the missed typhoid event and the false alarm.

## What the data looks like

* Orders: about 159 per day, 3.9 lines each. Channel mix: salesman 26%, voice note 24%, photo 16%, WhatsApp text 13%, phone call 12%, app 8%. Paper shops never use the app. Timing: morning rush 9-12, small afternoon bump, evening batch 20:00-23:30 (about 27% of all orders land after 20:00), salesman sheets 15:00-19:00, Sundays compressed to 9:00-14:00.
* Lines: 96.7% supplied, 1.3% substituted, 1.2% short, 0.8% not available. `raw_text` uses catalogue aliases, Hinglish number words, typos, and about 2.5% vague items ("bachchon ki bukhar wali syrup", "wahi jo kal bheja tha").
* Stock-outs concentrate where the story is: ORS (SKU0021) hits zero cover from 17 Nov, Dolo 120 syrup runs out from 11 Nov and Calpol 120 syrup is intermittently out from 4 Nov, zinc from 7 Nov, Dolo 650 falls under 1 day of cover. Event-pin ORS/zinc rows in `not_available_log` run at about 50 in six days against about 1 per six days normally.
* Claims: 48% expiry, 36% leakage, 16% breakage. Status 47% pending (young), 36% credited, 14% rejected, 3% partial. Median 74 days to credit among those credited, range 30 to 185 (right-censored by the 19 Nov cut-off).
* ASHA: 12 ASHAs, about 47% of ASHA-days missing (Sundays, holidays, leave spells, random misses). Three ASHAs file a Saturday weekly summary instead of daily. About 18% of reports are typed Hinglish; others Hindi or Marathi in Devanagari.

## Assumptions (one-line reason each)

1. History units are demand (what chemists asked for), so line `qty` reconciles with them and short or unavailable supply is recorded separately. Reason: history.csv has no supply column.
2. Chemist-day order headers group lines across medicine groups into 1 to 3 orders. Reason: real chemists send one list in the morning and one at night.
3. Channel preference depends on software and language (paper: voice, photo, salesman; marg: app, WhatsApp text, salesman). Reason: matches the street research on small paper shops.
4. `salesman_id` is the beat salesman who owns the chemist's account, even for orders the chemist sent directly. Reason: commission attribution is account-based (Imran's worry in D4).
5. Clerk minutes: voice 1.8 + 0.9 per line, photo 2.0 + 0.8, text 0.8 + 0.35, salesman sheet 0.6 + 0.4, phone 2.5 + 0.7, app 0.2 + 0.05, with gamma noise. Reason: listening and re-typing cost; app orders are near zero.
6. Pre-existing stock-out cause for the story: for six SKUs (two ORS, zinc, Dolo 650, Dolo 120, Calpol 120) company supply POs placed from 3 Nov land after about 22 Nov. Reason: needed so the stock radar and not-available log show a real shortage in the surge; it is scripted, not observed.
7. Reorder policy: reorder when stock plus pipeline falls under 11 days of 14-day mean dispatch, order 16 days, lead 3 to 6 days, 3% chance of a long supplier delay, no Sunday deliveries. Reason: simple stockist behaviour.
8. Batches on hand are split so they sum exactly to closing stock on 19 Nov; 20 SKUs get a batch expiring within 20 to 110 days. Reason: near-expiry stock for the returns story.
9. Prices: MRP drawn by form, PTR = 80% of MRP, ORS fixed at Rs 21 and Rs 24. Reason: needed for claim values; not real prices.
10. Claims are raised from 1 Jun 2026 (older than the window) so ageing buckets of 30 to 150 days exist; credit time is lognormal around 88 days; expiry claims more than 30 days past expiry are far more likely rejected. Reason: AIOCD and CDSCO return-window complaints in D4.
11. Schemes: ORS scheme `SCH001` (50+10, minimum 100, 12 to 20 Nov, 15 selected chemists including CH082) is the only one with a minimum large enough to bite; 21 background brand schemes (10+1, 5+1 and similar, some percentage discounts) apply to 85% of qualifying lines. Reason: matches the decoy and the AIOCD "selected chemists" complaint.
12. ASHA symptom counts are Poisson on household rates (fever 5.5%, diarrhoea 3.2%, cough 10% baseline), with a monsoon-tail seasonal decline. Events rise 3 to 6 days after the pharmacy story start by pin, concentrated in 2 to 3 "hot" localities per pin (others at 45% strength). Reason: ASHAs report what they see after care-seeking has started.
13. Bad-air week: citywide cough and breathing up to about 1.7x and 1.9x with a 2-day lag, fading after 17 Nov. Reason: respiratory story in the base set.
14. ASHA locality names appear in Latin script inside Devanagari snippets. Reason: speech-to-text keeps proper nouns in the speaker's script mix; avoids a transliteration table.
15. Official case baselines per 100,000 population per week: diarrhoeal disease 11, fever (dengue-like) 22, ARI 70, suspected malaria 2.2, jaundice 1.4; hospital admissions are 4 to 10% of that. Pins stand in for wards. Reason: plausible urban rates, not published figures.
16. Official lags: event onset 2 to 6 days after the pharmacy story start by pin, weekly aggregation, plus 3 to 6 days IDSP filing (+0 to 3 for slow wards), 7 to 14 days hospital, 5 to 10 days lab. Reason: literature range "none to about two weeks" (R5), varied on purpose.
17. The missed typhoid event (Dharavi, 28 Sep to 24 Oct, about 2.9x at peak) is added to official fever counts and lab typhoid positivity only; pharmacy and ASHA data stay near normal (ASHA fever 1.5x). Reason: user asked for one missed event.
18. `lab_positivity.csv` is the fictional LAB01 partner; the official file carries separate, larger "lab positivity" rows (1.4 to 2.4x the tests) from the municipal network. Reason: two independent sources.
19. Weather and air quality come from 4 Open-Meteo grid points (Kurla, Mankhurd/Govandi, Bandra, Andheri), each pin mapped to its nearest point; daily PM values are the mean of hourly values. Real weather does not match the seeded story, which is fine and kept honest.
20. Back-test breadth uses chemist-level counts from `order_lines`; groups evaluated: fever, diarrhoea, respiratory, allergy. Heat, eye, fungal and TB-watch volumes are too sparse for a stable 7-day signal.
