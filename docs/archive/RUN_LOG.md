# Backend run log

Real run of the backend on port 8001 with the live Gemini key, 21 Nov 2026 (about 00:00 to 00:30 IST), Windows 11, Python 3.11.9. Server and every helper process were stopped afterwards; demo state (`backend/.state`) was deleted.

Samples: `data/samples` (simulated voice notes and photos made for the demo). Expected answers: `*.expected.json`.

## 1. Order parsing, live Gemini (`POST /api/orders/parse`)

Model for all rows: `gemini-3.5-flash` (first in `GEMINI_MODEL_FAST`). Latency is the Gemini call itself, from the response field `latency_ms`.

| Message | Input | Language | Gemini latency | Lines | matched / uncertain / unknown | vs expected |
|---|---|---|---|---|---|---|
| msg_01 (`order_01.mp3`) | voice, Hindi | hi | 19.3 s (first run, default thinking: 43.6 s) | 6 | 5 / 1 / 0 | 6 of 6 SKUs and quantities right |
| msg_02 (`order_02.mp3`) | voice, Hindi | hi | 36.6 s | 6 | 5 / 0 / 1 | 6 of 6 right (the unknown is "बच्चों वाली सिरप", correctly left unresolved) |
| msg_03 (`order_03.mp3`) | voice, Marathi | mr | 43.7 s | 6 | 6 / 0 / 0 | 6 of 6 right; "Sporlac did not arrive last time" captured in `not_available` |
| msg_05 (`order_05.jpg`) | handwritten photo | en | 6.0 s (first run, default thinking: 16.3 s) | 6 | 6 / 0 / 0 | 6 of 6 right |

A second request for the same file is served from the disk cache in about 1 s.

Eval harness (`python -m tests.eval_parsing`), live, scored against `*.expected.json`:

```
sample           lines  sku ok  full ok  silent  uncert  unkn      ms  model
order_01.mp3         6       6        6       0       1     0   19290  gemini-3.5-flash
order_02.mp3         6       6        6       0       0     1   36560  gemini-3.5-flash
order_03.mp3         6       6        6       0       0     0   43667  gemini-3.5-flash
order_05.jpg         6       6        6       0       0     0    5996  gemini-3.5-flash
TOTAL expected lines 24: sku accuracy 100%, line recall (sku and qty) 100%, silent errors 0
```

`order_04.mp3`, `order_06.jpg` and `order_07.jpg` were NOT scored: by then every model in the chain was returning 429 or 503, and the harness refuses to count the pre-recorded fallback answer. Re-run when quota is back.

What the live runs found and fixed:

- "ORS 20" was matched as "could also be Omez 20" because the ordered quantity looked like a strength. Fixed in `catalogue.py` (quantity and unit words are stripped before matching, best of both readings wins). Regression tests added.
- Gemini transcribed Devanagari brand names; the validation step cannot spell-check those against Latin aliases, so such lines (for example "नॉरफ्लॉक्स TZ 15 पत्ते") stay `uncertain` with the reason "Could also be Norflox 400". This is deliberate: the clerk confirms.
- Thinking set to minimal for extraction cut one call from 8.5 s to 4.8 s in a direct test. `gemini-3.8-flash` rejects `MINIMAL` (HTTP 400), so it gets `LOW`, and any model that rejects the setting is retried with its default.

## 2. Agent (`POST /api/agent/explain`, diarrhoea alert `diarrhoea-400024`: Kurla East and Kurla West)

| Step | Result |
|---|---|
| Google Search grounding | FAILED on this key. HTTP 429 "exceeded your current quota" on `gemini-3.5-flash`, `gemini-3.8-flash`, `gemini-4-hydrogen`, `gemini-4-carbon`, in `v1` and `v1beta`, while plain (ungrounded) calls to `gemini-3.5-flash` worked at the same time. This looks like a zero or exhausted free-tier quota for the Search tool. No grounded source could be collected, so `sources` is empty and the response says so. |
| Reasoning call | `gemini-4-hydrogen` returned 429, 503 and 504 across retries; the chain fell back to `gemini-3.5-flash`, which answered in 29.2 s. |
| Result | Valid structured explanation: summary, 2 hypotheses (confidence 0.40 and 0.25, both labelled as hypotheses with "no external source supports an external cause"), distributor note, officer note ("moderate confidence, 59 percent ... not a confirmed outbreak"), 5 ranked ASHA localities taken from `localities.csv` (Qureshi Nagar, Kajupada, Kasaiwada, Nehru Nagar, Kapadia Nagar). |
| `grounded` / `search_note` | `false` / "No external sources found: the web search step failed." (honest, as designed) |
| First-call wall time | 139 s, almost all of it retries on failing models. Fixed since: a grounding 429 now fails fast (one try per model) and pauses search for 5 minutes. Second call of the same alert: 4.8 s (cached). |

The grounding code path (metadata to `sources`, `search_queries`) is covered by unit tests with a mocked response, but it has NOT been seen working against the real service. To get grounded sources in the demo, use a key or project with Search grounding quota (billing enabled).

## 3. ASHA loop

| Step | Result |
|---|---|
| `asha_03.mp3` live (Hindi, "everything fine, 2 mild coughs") | `gemini-3.5-flash`, 36.6 s, all 9 numeric/boolean fields equal the expected file. No open alert covers that pin code, so no confidence change (reported as such). |
| `asha_01.mp3` live | All models failed on the live attempt (429, 503, 504). Because it is a known demo recording, the API returned its pre-recorded reading, labelled `model: offline-sample` with the note "Gemini was unavailable just now ...". Fields matched the expected file by construction. |
| Confidence update | `diarrhoea-400024`: 59.4% to 91.2%, status `open` to `confirmed` (14 households, 5 diarrhoea cases against about 0.7 expected, water issue reported). |

## 4. Order approval and audit (cached parse of msg_01, clerk edits one quantity)

```
line_edited         Aman (clerk)  'ORS 20': qty 20 -> 25
uncertain_accepted  Aman (clerk)  'नॉरफ्लॉक्स TZ 15 पत्ते' was uncertain (75%) and was accepted as read: Norflox-TZ ...
order_approved      Aman (clerk)  Approved 6 lines (95 units) for Al-Shifa Medical & General Stores; 1 edited, 1 uncertain accepted as read.
asha_report         ASHA03        ASHA report from Bhim Nagar: 14 households visited; Diarrhoea and vomiting 59% -> 91%.
```

`/api/metrics` after that session: auto-matched 83.3%, uncertain 16.7%, unknown 0%, edit rate 16.7%, 1 alert confirmed, 3 alerts raised, 1 decoy suppressed, alert precision 1.0 (one decided alert).

## 5. Seed-data signal (as of 2026-11-19)

| Alert | Level | Pins | Ratio vs normal | Breadth | Confidence (orders only) |
|---|---|---|---|---|---|
| `diarrhoea-400019` | alert | 400019 Matunga, 400022 Sion/Chunabhatti | 6.6x | 0.41 | 0.70 |
| `diarrhoea-400024` | alert | 400024 Kurla East, 400070 Kurla West | 3.7x | 0.25 | 0.59 |
| `fever-400043` | alert | 400043, 400088 Mankhurd (dengue-like, respiratory flat) | 2.5x | 0.27 | 0.58 |

Decoy: 400086 diarrhoea is 3.4x with breadth 0.0 (one shop). It does not alert and is listed in `suppressed`. It sits next to the Kurla cluster and is not promoted, because its chemist participation is not rising.

## 6. Gemini model availability seen with this key

| Model | Observed |
|---|---|
| `gemini-3.5-flash` | Works; 5 to 45 s per call for these inputs; intermittent 429 |
| `gemini-3.8-flash` | Frequent 503 and 504 ("high demand"); rejects thinking level MINIMAL |
| `gemini-2.5-flash`, `gemini-2.5-pro` | 404 "no longer available to new users" (the chain skips them) |
| `gemini-4-hydrogen` | 429, 503 and 504 in these runs |
| `gemini-4-carbon` | 429, free tier limit 0 |
| `gemini-omni-flash-preview` | 429 |
| Google Search grounding | 429 on every model tried |

Resilience built in because of this: model fallback chain, `Retry-After` honoured up to 45 s, a 150 s total budget per request, labelled fall-back to the pre-recorded reading for known demo samples, disk cache, and `python -m app.warm` to fill the cache before the demo.

## 7. Tests

`python -m pytest`: 74 passed (about 20 s, no network). Includes the seed-data back-test, API smoke tests with `DEMO_OFFLINE=1`, mocked Gemini failure modes, and the agent with mocked grounding.
