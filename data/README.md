# FirstSign seed data

Everything in this folder is **simulated demo data**. The pin codes, area names, wards and landmarks are real places used for realism. Chemist shops, owners, the distributor, ASHAs, order history, populations and household counts are invented or rough estimates. No real patient names appear anywhere. The UI must label history as "Simulated history for demo".

## Files

| File | What it is |
|---|---|
| `catalogue.csv` | 160 real Indian brands sold at Mumbai chemists, with strength, form, pack, molecule, group, unit and 3 to 8 aliases each (how chemists say and write the name: Hinglish spellings, abbreviations, misspellings). Capsules are classed as form `tablet` because the contract has no capsule form. Combination-syrup strengths should be verified before any real-world use. |
| `groups.json` | The 11 fixed medicine groups, with English and Hindi labels, a colour hint and `is_chronic`. |
| `pincodes.csv` | 20 pin codes in the Kurla, Sion, Chembur, Dharavi, Ghatkopar, Bandra and Andheri belt. Centroids and catchment populations are approximate. |
| `chemists.csv` | 150 fictional chemist shops spread over those pins (owner first names only), with jittered coordinates, language (hi/mr/en) and software (about 65% paper). |
| `distributor.json` | The fictional demo stockist "Sai Krupa Pharma Distributors", Dava Bazaar. It serves 120 of the 150 chemists, at least 4 in every pin. |
| `history.csv` | 90 days ending 2026-11-19, one row per day x pin x group (19,800 rows): `units` and `chemists_ordering`. Counts are the distributor's orders only. |
| `asha.csv` | 12 ASHAs (first names only) across 9 pins, language hi or mr. |
| `localities.csv` | 120 localities (6 per pin): chawls, nagars, markets, building clusters, with household estimates and jittered coordinates. Locality ids look like `400024-02`. |
| `demo_inbox.json` | The 10 incoming messages for 20 Nov 2026: 4 voice notes, 3 photos of handwritten chits, 3 WhatsApp texts. Each points to its media and its ground-truth JSON. |
| `samples/` | The media and ground truth for the inbox and for the ASHA reports (see below). |
| `tools/` | The generators and the validator. |

## Samples

* `order_01..04.mp3`: voice orders (three Hindi, one Marathi). Spoken text is Devanagari with brand names as a chemist would say them.
* `order_05..07.jpg`: handwritten chits on lined paper (Kalam handwriting font, tilt, shadow, noise). `order_07` has a crossed-out line that is not an order.
* `order_08..10.expected.json`: the three text messages (their text is in `demo_inbox.json`).
* `asha_01..04.mp3`: ASHA visit reports (`asha_01`, `asha_03`, `asha_04` Hindi, `asha_02` Marathi). Each is a different story: dirty-water diarrhoea cluster (Bhim Nagar), the same in Sion (Marathi), a quiet report from the decoy pin (Asalpha) that should cancel its alert, and a dengue-like fever report (Lallubhai Compound).
* Every sample has `<name>.expected.json`. For orders this is a `ParsedOrder` exactly as in ARCHITECTURE.md section 5, with `model: "ground_truth"` and `latency_ms: 0`. For ASHA reports it is the structured report (language, transcript, `households_visited`, `fever`, `diarrhoea`, `cough`, `breathing`, `rash`, `children_affected`, `referred`, `water_issue_reported`, `notes`) plus `asha_id` and `locality_id`. These drive offline mode and the QA accuracy checks.

Conventions in the ground truth:

* `transcript` is the spoken or written content (Devanagari for Hindi and Marathi voice, as written for text and photos). `raw_text` on each line is a Roman-script version of what the sender called the item.
* `status: matched` lines have no alternatives. `uncertain` lines carry a best-guess `sku_id` and ranked `alternatives` (for example "pan dee", "PCM 500", "Calpol syp"). `unknown` lines have `sku_id: null` ("woh bachchon wali syrup").
* `not_available` lists items the sender says were short or unavailable. They may also appear as order lines, because the sender asks for them again.
* ASHA counts: `diarrhoea`, `fever`, `cough`, `breathing` and `rash` are the number of households with the symptom; `children_affected` and `referred` are people. A symptom that is not mentioned is 0.

Audio is synthesised with gTTS (one female voice), so accents do not vary. Gemini audio and image generation returned `429 RESOURCE_EXHAUSTED` on the free-tier key, so gTTS and a PIL renderer were used. A real recording or photo can replace any file as long as the name is kept.

## How the history was seeded

`tools/generate.py` is deterministic (`numpy` seed 20261119). For each served chemist, group and day it draws an order count and order sizes from a per-group base rate, then multiplies by a Monday-heavy weekday pattern (Sunday 0.45), a month-end push (days 28 to 1: x1.35 chronic, x1.15 others) and a slow seasonal drift from late monsoon to November. Chemists vary in size and in affinity per group. Chronic groups carry no events.

Four seeded events (the last six days of the data are the "now" of the demo):

1. **Water-borne diarrhoea.** 14 to 19 Nov, ramping up. Kurla West 400070, Kurla East 400024 and Sion / Chunabhatti 400022 (about 85% of chemists affected, peak x3.6, so roughly 2.3x to 4x of the 4-week normal over the window, strongest in Sion). Antop Hill 400037 gets a weaker echo (about half the chemists, peak x2.0) as a watch-level neighbour.
2. **Dengue-like fever.** 10 to 19 Nov, ramping up, in Mankhurd 400088 and Govandi 400043 (95% of chemists, peak x2.9, about 1.8x to 2.1x). Respiratory stays at its normal level there.
3. **Bad-air week.** 10 to 19 Nov, citywide respiratory bump (90% of chemists, peak x1.5, plateau 12 to 15 Nov, fading after). A good signal engine discounts this because every pin moves together.
4. **ORS scheme decoy.** In Ghatkopar West 400086, chemist `CH082` bulk-orders ORS on 13, 15, 17 and 18 Nov (120 to 150 sachets each). Pin volume is about 2.5x normal but the number of chemists ordering is unchanged, so breadth is flat and it must not alert. `CH082` is kept out of the demo inbox.

## Regenerate and validate

```
python -m pip install pandas numpy pillow gTTS
python data/tools/generate.py      # all CSV/JSON, inbox and expected files (about 4 s)
python data/tools/make_media.py    # voice notes and chit photos (needs network for gTTS)
python data/tools/validate.py      # schema, foreign keys, sample paths, event story; exit 1 on failure
```

`generate.py` rewrites the expected JSON files, so re-run `make_media.py` after changing any transcript. The handwriting font `tools/fonts/Kalam-Regular.ttf` is from the google/fonts repository (SIL Open Font License).
