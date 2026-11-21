# QA report: functional and Gemini quality (21 Nov 2026, QA engineer 1)

Scope: API contract, pytest, parsing accuracy on every sample, latency, uncertainty behaviour, signal, agent, ASHA loop, audit, offline mode, restart persistence, security basics. Server on port 8010, stopped afterwards. About 30 live Gemini calls used.

## Headline numbers (quotable)

- pytest: 74 passed (about 40 s).
- Live parsing accuracy, 10 inbox samples (4 voice, 3 photo, 3 text), model gemini-3.1-flash-lite, no cache, no offline fallback:
  - Expected lines 56, returned 55. SKU recall 55/56 = 98.2%. SKU+qty recall 55/56 = 98.2%. Precision 55/55 = 100% (no invented or wrong lines).
  - Wrong-and-green ("silent") errors on sku or qty: 0. The one miss is a dropped line (msg_03 Electral), not a wrong one, and it is not flagged.
  - Status calibration: 2 of 3 expected-uncertain items correctly flagged (pan dee, unnamed syrup); 2 expected-uncertain items came back green (Calpol syp in msg_06, PCM 500 in msg_07). 5 of 5 lines in msg_02 were wrongly flagged uncertain with nonsense reasons (F2).
- Latency (live, flash-lite): 3.6 to 8.5 s per parse, p50 about 6 s. Earlier cached gemini-3.5-flash runs recorded 19 to 44 s. ASHA voice report 4.5 to 5.9 s. Agent explain 6.3 s (ungrounded).
- ASHA structuring: 35 of 36 fields match the expected JSON across 4 samples (Hindi x3, Marathi x1). The one diff is water_issue_reported on asha_04 (standing water and mosquitoes; arguably correct).
- Signal back-test: both seeded events alert, decoy 400086 is suppressed with a plain reason, approved orders move counts (+58 units in 400070 diarrhoea after approving a 58-unit order).

## Blocking environment fact

The key is on the free tier. gemini-3.5-flash, gemini-3.8-flash, gemini-4-carbon, gemini-omni and gemini-flash-latest return 429 "limit: 20 requests per day", retry in about 12.5 h, which is after the 9:00 IST deadline. Google Search grounding returns 429 on every model. gemini-4-hydrogen returns 503. Only gemini-3.1-flash-lite worked, and it is not in the default chain. See F1.

## Findings

### F1 (blocker) Default model chain has no working model; live demo and judges' use will fall to canned output
With the default chain every parse hits 429/429/404 in about 2 s and returns `offline-sample`; unknown uploads return nothing. `gemini-3.1-flash-lite` works (parse, ASHA, agent reasoning) and is absent from `GEMINI_MODEL_FAST/REASON`. Fix: add `gemini-3.1-flash-lite` (and `gemini-3.1-pro-preview` if available) to both chains; drop `gemini-2.5-flash` (always 404, costs a round trip per request); enable billing on the key's project or use a paid key for the deployed service; re-run `python -m app.warm` with the working model so the Docker image ships a warm cache (only 5 of 10 inbox messages and no explain result were warm).

### F2 (high) Devanagari transcripts make correct matches look wrong
Voice parse of msg_02 returned all five correct SKUs as `uncertain` (confidence 0.45 to 0.67) with misleading reasons, for example Zincovit: "the spelling is closer to Paracetamol IP (generic)"; ORS: "closer to Losar 50"; "Pan-D ... closer to Levocet-M". Cause: raw_text is Devanagari ("ओआरएस", "ज़िनकोविट") and the fuzzy matcher compares it to Latin aliases. The clerk sees five yellow lines and wrong explanations. Fix: ask Gemini for a Latin-script `raw_text`/brand reading alongside the original, or transliterate before fuzzy matching, and never print a "closer to X" reason for an unrelated brand. msg_01 and msg_03 (Latin brand names inside Devanagari) did not show this.

### F3 (high) Offline-sample mode does not reproduce the designed uncertainty
In `DEMO_OFFLINE=1` (and in the offline fallback) msg_02 returns "pan dee" as `matched` (expected `uncertain`) and the unnamed children's syrup as `uncertain` with a suggested "Alex Syrup" (expected `unknown`, null SKU). The notes still say two lines need the clerk, so the screen contradicts itself. The offline path is the safety net for the demo; the three-colour story (green, yellow, red) breaks there. Fix: when serving a bundled sample offline, return the `.expected.json` lines unchanged and do not re-run them through the catalogue matcher.

### F4 (medium) Silent normalisation of ambiguous or misspelt input shown as green
Live text parse: "pan 20 patta" became Pan 40, status `matched` 0.96, while the model's own note says "interpreted as Pan 40". "crosin 30" became Crocin Advance, `matched` 0.92. Contract rule: nothing silently corrected. Calpol syp (msg_06) and PCM 500 (msg_07) also came back green where the sample marks them uncertain. Fix: if the model's notes or raw_text differ from the brand beyond a threshold, or more than one catalogue item shares the base name, cap status at `uncertain` with a reason.

### F5 (medium) A spoken line can be dropped with no flag
msg_03 (Marathi voice): the live reading omitted "electral 15". Nothing in notes or status says a line may be missing. Fix: add a prompt instruction to list any word it could not place in `notes`, or compare the count of numbers in the transcript to line count and warn on mismatch.

### F6 (medium) Corrupt or non-media files return 502 upstream_error and burn quota
A 3 KB random `.mp3`, a text file named `.mp3` and HTML named `.jpg` all go to Gemini and come back `502 upstream_error` after the model returns 400. Expected: a 400/422 "could not read this audio/image". Fix: treat Gemini 400 as bad input (do not retry other models), and sniff magic bytes before the call. Empty file (400), `.txt` (400), 30 MB file (400 "larger than 20 MB"), unknown chemist (404) are handled well.

### F7 (medium) Search grounding unverified; agent runs ungrounded with an honest label
Every grounded call returned 429, so `sources` is empty, `grounded:false`, `search_note` "No external sources found: the web search step failed". The honesty is good, but the 20% Google-AI criterion cannot show grounded URLs today, and in offline mode there is no sample grounded result at all. Fix: with a billed key, run the explain once for each of the three alerts and keep them in the warm cache; consider a clearly labelled pre-recorded grounded sample for offline mode.
The ungrounded run also wrote "no external reports are currently available" while stating a 3.7x surge; acceptable, and visit list IDs were all valid localities (checked against /api/localities).

### F8 (medium) ASHA report can be duplicated and attributed across pins
Posting the identical report twice counts twice (confidence 0.912 to 0.877 to 0.831 for two identical zero reports). Known (CONTRACT_REQUESTS item 2). Also ASHA03 (pin 400024) could file a report for locality 400070-01 (200 OK); no check that the ASHA works in that pin. Fix: dedupe on (asha_id, locality_id, transcript hash, day) and reject cross-pin reports with 422.

### F9 (medium) One report moves an alert from 0.59 to 0.91 and confirms it
A single report with 5 cases in 14 households took diarrhoea-400024 from open 0.594 to confirmed 0.912 (delta 1.96). Direction and reasons are correct and the rule is as specced, but this reads as overconfident for a single field visit. Consider damping (cap the per-report delta) so judges do not question the model.

### F10 (low) Alert 400024 diarrhoea at level `alert` with breadth 0.06
The decoy is suppressed at breadth 0.0, yet pin 400024 alerts at breadth 0.06 because it is grouped with 400070 (breadth 0.44). The alert-level breadth is 0.25. Explainable, but the signal cell for 400024 contradicts the "low breadth does not alert" message if a judge clicks it. Also the respiratory "bad-air" bump in the seed story produces no watch cell, so it never shows.

### F11 (low) Offline free-text rules lose quantities
`offline-rules` on "ors 10, pan d 5, dolo 650 20" gives qty 1 for all three and maps "ors 10" to SKU0113 (flagged uncertain). With a unit word ("dolo 650 20 strip") qty is right. Gibberish "zzzz qqqq 5 strip" maps to Zinc (uncertain) instead of unknown. Offline uploads of non-bundled audio return an empty order with a clear note, which is fine.

### F12 (low) Smaller items
- `/api/signal?days=` is capped at 60 though history is 90 days; 91+ returns 422. Not in the contract.
- No length limit on `text` (160 KB accepted and sent to Gemini).
- Telemetry counters reset on restart (state persists, telemetry does not).
- A crossed-out item (msg_07 "Avil 25") is listed under `not_available`; it is really "cancelled by sender". Handled well otherwise (the notes say it was crossed out).
- `created_at` timestamps are UTC (`+00:00`) while inbox times are IST; show IST in the UI.
- Fallback loop logs a 404 for `gemini-2.5-flash` on every request.

## What passed

- All 20 GET endpoints return 200 with contract shapes; unknown alert, unknown inbox media, bad ASHA and locality return JSON 404 `{error:{code,message,request_id}}`; bad enums and missing fields return 422; negative, zero and huge quantities are rejected; duplicate approval returns 409; line with no SKU returns 400.
- Audit: approving an edited order wrote `order_approved`, `line_edited` (before/after) and `line_removed`; ASHA reports and action approvals are logged. Edited text and a re-ordered visit list are honoured, and `/api/asha/visits?asha_id=ASHA03` returns only her pin's localities.
- Dismissal rule works: two near-zero reports on fever-400043 took it 0.575 to 0.419 to 0.277 and `dismissed`. Confirmation works (above).
- Restart persistence: orders, audit, alert statuses and reports survive a server restart; `/api/demo/reset` clears them.
- Offline mode (`DEMO_OFFLINE=1`): `/api/health.offline` true; all 10 inbox messages, 4 ASHA samples and the agent respond in about 2 s, labelled `offline-sample` / `offline-rules`, with "Offline demo mode: no web search was run".
- Security: the key prefix appears only in `.env`; not in `frontend/dist`, `backend/.cache`, any response, or any of the six server logs. `/.env` and path-traversal attempts return the SPA page or a JSON 404, not the file. `.env` is git-ignored. Upload cap 20 MB enforced.

## Not covered

Browser flows (MediaRecorder, map, phone width) were not exercised; Firestore and BigQuery paths untested; Docker image not built (daemon off); grounded sources not verified live (quota).
