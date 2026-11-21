# FirstSign: architecture contract (v1, 20 Nov 2026)

This file is the contract every team member builds against. Change it only through the tech lead. If you need something it does not define, add it to `docs/CONTRACT_REQUESTS.md` and pick the simplest compatible choice.

## 1. Product in one paragraph

FirstSign reads the WhatsApp voice notes and handwritten-list photos that Indian chemists send their medicine distributor, and turns them into ready-to-bill orders.

Because every order passes through, FirstSign also sees which medicine groups (fever, diarrhoea, respiratory and so on) are rising in each pin code compared with normal. It shows this in three ways:

1. **Distributor view:** a stock radar ("stock up on these, here's why").
2. **Health officer view:** a ranked list of where ASHA workers should visit next.
3. **ASHA view:** each ASHA records her visit observations as a voice note in her own language.

Her report moves the alert: one report raises or lowers its confidence, and **two independent reports are needed to confirm** it (a near-zero report lowers it). Each report becomes labelled ground truth.

**Gemini's jobs:** reading voice, reading handwriting, matching to the catalogue, structuring ASHA reports, and running an agent that explains why an area is rising (using Google Search) and drafts the actions. A human approves every outbound action.

## 2. Repo layout (each owner writes only in their area)

```
firstsign/
  ARCHITECTURE.md            tech lead
  README.md                  integration
  .env / .env.example        GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT=firstsign-buildathon, GOOGLE_CLOUD_REGION=asia-south1
  docs/                      product (PRODUCT.md, METRICS.md, DEMO_SCRIPT.md, DECK.md), design (DESIGN.md), qa (QA_REPORT*.md)
  data/                      data engineer: seed CSV/JSON + samples/ (audio, images)
  backend/                   backend developer
    app/
      main.py                FastAPI app, mounts /api and serves frontend/dist at /
      config.py              env settings
      models.py              pydantic models (the API types below)
      gemini.py              client, model fallback chain, retries, structured output helpers
      parsing.py             order parsing (audio, image, text) and ASHA report parsing
      catalogue.py           brand/SKU matching (exact, fuzzy, phonetic); Gemini returns sku_id or "unknown"
      signal.py              baselines, ratios, breadth, co-movement, alert levels, confidence
      agent.py               the explain-and-draft agent (Gemini tool use + Google Search grounding)
      store.py               storage interface; LocalStore (in-memory, seeded from data/) default; FirestoreStore optional
      bq.py                  optional BigQuery path (export counts, AI.FORECAST baseline); never required to run
    tests/                   pytest
    requirements.txt
  frontend/                  frontend developer (Vite + React + TypeScript + Tailwind), builds to frontend/dist
  infra/                     integration: Dockerfile (multi-stage), deploy.sh (Cloud Run asia-south1), cloudbuild.yaml optional
```

## 3. Runtime rules

- **Python 3.11.** FastAPI, uvicorn, pydantic v2, google-genai, python-multipart, rapidfuzz, pandas.
- **Optional:** google-cloud-firestore, google-cloud-bigquery. Imported lazily.
- **Runs locally with only `GEMINI_API_KEY`.** No other cloud service is required.
  - `STORAGE=local|firestore` (default local).
  - `SIGNAL_BACKEND=local|bigquery` (default local).
- **Gemini models.** Read from env, with a fallback chain on 429/503:
  - `GEMINI_MODEL_FAST`: default `gemini-3.5-flash`, then `gemini-3.8-flash`, then `gemini-2.5-flash`. Used for parsing.
  - `GEMINI_MODEL_REASON`: default `gemini-4-hydrogen`, then `gemini-3.5-flash`. Used for the agent.
  - **Always use structured output** (response JSON schema) for parsing.
  - **Retries:** exponential backoff, max 3.
- **Gemini engineering (21 Nov 2026).** Full detail and measured numbers in `docs/GEMINI_ENGINEERING.md`.
  - Every call goes through `GeminiClient` and is written to the usage ledger (`app/usage.py`: tokens by type, latency, cache hit, fallback, error code, INR cost). `GET /api/ai/usage` summarises it.
  - Parse prompt layout: instructions + compact catalogue in the system instruction (identical every call, so implicit caching can match it), the variable text or media after it. Thinking level per job: `minimal` for parsing, `low` for search, `medium` for the agent. Photos at `media_resolution=high`. `max_output_tokens` per job.
  - Protection: concurrency semaphore (`GEMINI_MAX_CONCURRENCY`), per-IP rate limit on parse/send/report/explain (`RATE_LIMIT_PER_MIN`, 429 + `Retry-After`, `app/ratelimit.py`), jittered retry honouring `Retry-After`, daily spend guard (`DAILY_GEMINI_BUDGET_INR`, default 300) that falls back to labelled saved results, 20 MB upload and 4,000-character text caps.
- **Mock mode.** If `GEMINI_API_KEY` is missing or `DEMO_OFFLINE=1`, parsing returns deterministic canned results from `data/samples/*.expected.json` so the demo never dies.
- **Data rules:**
  - No patient names stored.
  - Orders store chemist ID, pin code, items and time only.
  - ASHA reports store counts, not names.
  - Media files are processed in memory and not kept beyond the request (demo samples excepted). The one exception is media a chemist sends through `POST /api/chemist/send`: it is kept under `backend/.state/media` so the clerk can replay it, and is not cleared by the demo reset.
- **The demo history is SIMULATED.** The UI must label it ("Simulated history for demo").

## 4. Data files (`data/`, owned by the data engineer)

| File | Columns / shape |
|---|---|
| `catalogue.csv` | sku_id, brand, strength, form (tablet/syrup/sachet/drops/inhaler/respule/cream/injection), pack, molecule, group, unit (strip/box/bottle/sachet/tube/vial), aliases (pipe-separated spoken/written variants, e.g. "pan d\|pan-d\|pantop d") |
| `groups.json` | id, label, label_hi, color_hint, is_chronic |
| `pincodes.csv` | pin, area, ward, lat, lng, population |
| `chemists.csv` | chemist_id, shop_name, owner_first_name, pin, lat, lng, language (hi/mr/en), software (paper/marg/other) |
| `distributor.json` | the demo distributor: name, area served, chemist_ids |
| `history.csv` | date, pin, group, units, chemists_ordering. 90 days ending 2026-11-19, simulated, with seeded events (see below) |
| `asha.csv` | asha_id, first_name, pin, language |
| `localities.csv` | pin, locality_id, name, landmark, lat, lng, households (lanes/chawls/buildings used for visit lists) |
| `demo_inbox.json` | the order messages shown in the inbox: id, chemist_id, received_at, type (voice/photo/text), text (for text), media (path under data/samples), expected (path to expected JSON) |
| `samples/` | order_*.(wav\|mp3\|ogg), order_*.(jpg\|png), asha_*.(wav\|mp3), each with a matching `.expected.json` |

**Groups (fixed IDs):** fever, diarrhoea, respiratory, allergy, heat, fungal, eye, tb_watch, chronic_bp, chronic_diabetes, other. The chronic groups are the stable denominator.

**Seeded events in history (so the demo tells a story):**
- **Diarrhoea (water-borne)** rising in 2-3 neighbouring pin codes (Kurla 400070, Sion 400022, Chunabhatti 400022/400024 area) over the last 6 days, about 2.5x normal, with many chemists ordering.
- **Fever with flat respiratory** (dengue-like) rising in one or two other pin codes over the last 10 days, about 1.8x.
- **A respiratory bump** across many pin codes tied to a bad-air week.
- **A decoy:** one chemist bulk-ordering ORS on a scheme. High volume, low breadth, so it must NOT alert.

## 5. API (FastAPI, all JSON, prefix `/api`)

**Line item (`OrderLine`)**

```
OrderLine { raw_text, sku_id|null, brand|null, strength|null, form|null, molecule|null, group|null, qty, unit,
            confidence (0-1), status: "matched"|"uncertain"|"unknown", alternatives: [{sku_id, brand, score}] }
```

**Parsed order**

```
ParsedOrder { message_id|null, chemist_id, language, transcript, lines: [OrderLine], not_available: [string],
              notes, model, latency_ms }
```

**Endpoints**

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{status, model_fast, model_reason, storage, signal_backend, offline}` |
| GET | `/api/catalogue` | |
| GET | `/api/groups` | |
| GET | `/api/pincodes` | |
| GET | `/api/chemists` | |
| GET | `/api/distributor` | |
| GET | `/api/inbox` | Bundled messages plus messages chemists sent through the app (`source:"chemist_send"`, `media_url`). Status `new\|parsed\|approved` and the parsed result if any |
| POST | `/api/orders/parse` | Multipart: `file` (audio or image) or form field `text`, plus `chemist_id`, optional `message_id`. Returns `ParsedOrder` |
| POST | `/api/orders` | Body: `{chemist_id, message_id, lines (as approved by the clerk), approved_by}`. Saves the order, updates live counts, writes an audit entry. Returns `{order_id}` |
| GET | `/api/orders` | Recent approved orders |
| GET | `/api/audit` | Who approved what and when; every line edit recorded (design for blame) |
| GET | `/api/signal` | Query `days=30`. Returns `{as_of, cells:[{pin, group, today, baseline, ratio, z, breadth, level:"normal"\|"watch"\|"alert", series:[{date, units, baseline}]}]}` |
| GET | `/api/alerts` | `[{alert_id, pins, group, level, ratio, breadth, started, confidence, status:"open"\|"confirmed"\|"dismissed", asha_reports}]`, built from co-movement rules |
| GET | `/api/radar` | Distributor stock radar: `[{pin, area, group, skus:[{sku_id, brand, suggested_qty, reason}], ratio, chemists_affected}]`. With `data/extended`, items chemists could not get last week rank first, `suggested_qty` adds the units already missed, and `reason` reads like "0 days of cover, 6 chemists in Sion asked last week. 241 units cover 5 days at today's pace plus 124 units already missed." |
| POST | `/api/agent/explain` | Body `{alert_id}`. Returns `{summary, likely_causes:[{cause, evidence, confidence}], sources:[{title, url}], actions:{distributor_note, officer_note, asha_visit_list:[{locality_id, name, landmark, priority, reason}]}, model, latency_ms}`. Uses Gemini with Google Search grounding plus our own data as tool results. Cache per alert |
| POST | `/api/actions/approve` | Body `{alert_id, action:"distributor_note"\|"officer_note"\|"asha_visit_list", approved_by, edited_text?}`. Logs to audit |
| GET | `/api/asha/visits` | Query `asha_id`. Her ranked visit list, after the officer approved one |
| POST | `/api/asha/report` | Multipart: `file` (audio) or `text`, plus `asha_id`, `locality_id`. Gemini structures it into `{language, transcript, households_visited, fever, diarrhoea, cough, breathing, rash, children_affected, referred, water_issue_reported (bool), notes}`. Updates the alert's confidence and status. Returns that object plus `{alert_id, new_confidence}` |
| GET | `/api/metrics` | `{orders_parsed, lines_parsed, auto_matched_pct, uncertain_pct, avg_latency_ms, asha_reports, alerts_confirmed}` |

**Parse fixes (21 Nov).** `ParsedOrder` also carries `struck_out: [string]`: items crossed out on a handwritten list. The model is told to report them there and never as lines; any that still arrive as a line are forced to `unknown` with the reason "Crossed out on the list", so they can never be green. Interactive parses are capped at 25 s (`PARSE_DEADLINE_S`, applied to each HTTP call as well); if a bundled demo sample is slower, the labelled pre-recorded reading is shown and a background thread keeps trying with a 150 s budget (`WARM_DEADLINE_S`) so the next parse is a cache hit. Clean Latin-script brand names inside Hinglish sentences ("ondem 4 ke 8 patte", "zinc 20 dt 15 strip") now match green; real doubt (misspellings, bare shared names, wrong strengths) is still flagged.

**Extended simulated data and chemist send (added 21 Nov).** All JSON, all labelled `simulated:true` except weather. Loaded lazily from `data/extended/`; if a file is missing the endpoint answers 200 with an empty result and an honest note (body field `note`, or header `X-Data-Note` for list responses), never a 500. "Today" for these views is the last day of the simulated window (2026-11-19, or `DEMO_AS_OF`).

| Method | Path | Response |
|---|---|---|
| GET | `/api/overview` | `{orders_30d, lines_30d, chemists_active, share_by_channel:{voice_note, photo, whatsapp_text, salesman, phone_call, app} (fractions summing to 1), stockouts_14d (distinct SKUs reported not available), stockout_events_14d, avg_clerk_minutes_saved_per_order (ESTIMATE), avg_clerk_minutes_saved_basis, alerts_open, alerts_confirmed, window_days:30, as_of, simulated:true, note}`. 30 days of simulated orders plus orders approved live |
| GET | `/api/backtest` | `{simulated:true, note, rule, events:[{event, pin, area, group, signal_first, asha_rise\|null, official_date\|null, lead_days_vs_official\|null, lead_days_vs_asha\|null, data_status:"projected_sim"\|"observed_sim"}], false_alarms:[{pin, group, alert_date, official_elevated, asha_rise, cause, verdict, data_status}], missed:[{event, pin, group, official_first_elevated_week_start, official_date, peak_typhoid_lab_positivity_pct, pharmacy_fever_peak_ratio, why_missed, data_status}], decoys:[...], median_lead_days_vs_official, median_lead_days_vs_asha}`. `?alert_id=` filters to the alert's pins and group and adds `filtered_by`. A SIMULATED scenario replay, never real evidence |
| GET | `/api/environment` | `?pin=&days=30` (max 90). `[{date, temp_max, temp_min, precip_mm, humidity, pm25, pm10, source:"open-meteo"}]`. REAL data, nearest grid point. Header `X-Data-Note` |
| GET | `/api/stockouts` | `?days=14`. `[{sku_id, brand, group, pins:[...], chemists, qty_wanted, days_of_cover\|null}]`, most chemists first. Simulated log plus live "not available" mentions read from parsed messages |
| GET | `/api/asha/history` | `?pin=&days=30`. One row per day, zeros where no ASHA reported: `[{date, households_visited, fever, diarrhoea, cough, referred, reports}]`. Simulated reports plus live ones. `pin` omitted gives all pins |
| POST | `/api/chemist/send` | Multipart: `chemist_id`, and `file` (audio or image) or `text`. Creates a new inbox message and returns `{message_id, status:"new"}`. Junk media gives 400 `invalid_media`, unknown chemist 404 |
| GET | `/api/media/{message_id}` | The audio or image of any inbox message (bundled or sent through the app), for replay. 404 for a text message |

**Confidence rule (simple, explainable):** `confidence = signal strength (ratio and z, capped) x breadth factor (share of chemists in that pin ordering above normal) x co-movement bonus`, then updated by ASHA reports. Reports with symptom counts above an expected background rate raise it; reports with near-zero counts lower it. Show the reasons in plain words.

**AI usage:** `GET /api/ai/usage` returns `{totals, by_job, by_model, cache{disk_hit_rate, implicit_cached_token_share}, fallback_rate, error_rate, latency_ms{p50,p95}, cost_per_order_inr, budget{daily_inr, spent_today_inr, remaining_inr, exceeded}, assumptions{usd_inr, prices_usd_per_1m}, limits}`. The four Gemini endpoints (`/orders/parse`, `/chemist/send`, `/asha/report`, `/agent/explain`) can answer 429 `rate_limited` with a `Retry-After` header.

## 6. Frontend (Vite + React + TS + Tailwind)

**Routes:**
- `/`: landing with the three role entrances.
- `/distributor/inbox`
- `/distributor/radar`
- `/officer`: map and alerts.
- `/officer/alert/:id`: agent explanation, drafted actions, approve.
- `/asha`: mobile-first; visit list, record voice report, see it structured, confirm.
- `/about`: how it works, data rules, simulated-data notice.

**Rules:**
- The map uses Leaflet with OpenStreetMap tiles. Circles at pin-code centroids, sized and coloured by level.
- The browser records audio with MediaRecorder; upload of files is also supported.
- Uncertain lines are yellow, unknown lines are red, and nothing is ever silently corrected.
- Hindi labels where natural.
- Accessible: keyboard, contrast, aria labels.
- Works at phone width (the ASHA view especially).

## 7. Definition of done

1. `uvicorn app.main:app` from `backend/` serves the built frontend and the API on one port.
2. Every endpoint works against seeded data.
3. Real Gemini parsing works on the samples.
4. The agent returns grounded sources.
5. `pytest` passes.
6. The Docker image builds.
7. `infra/deploy.sh` deploys to Cloud Run in `firstsign-buildathon`, `asia-south1`, when gcloud is authenticated and billing is on.
