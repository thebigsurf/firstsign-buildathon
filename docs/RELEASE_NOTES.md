# FirstSign: release notes (final QA, 21 Nov 2026, about 06:40 IST)

All history, chemists, ASHA reports, official cases and lab data are SIMULATED and labelled so in the product. The back-test is a replay of a simulated scenario, not evidence. Weather and air quality are REAL (Open-Meteo) and labelled real. No real patient names.

## What works (verified today)

- Chemist role (`/chemist`): send text, a voice note or a photo; it lands in the distributor inbox as a new message with its media (`POST /api/chemist/send`, `GET /api/media/{id}`). Junk media returns 400, unknown chemist 404.
- Distributor inbox: Gemini reads voice notes and handwritten photos (Hindi, Marathi, English); green, yellow and red lines with reasons; crossed-out lines are listed as "crossed out", never as orders; every approval is logged; a duplicate approval gives 409.
- Stock radar: ranks SKUs using days of cover and the last 7 days of "not available" requests per pin code (`/api/radar`), plus a stock-outs table (`/api/stockouts`).
- Health officer: three alerts, a Gemini explanation with drafted actions, a ranked ASHA visit list, human approval. The alert page also shows the simulated back-test, real weather and air, and ASHA history.
- ASHA: voice reports. Two reports from two ASHAs confirm an alert (confidence 0.799, then 0.915, status confirmed).
- Landing tiles from `/api/overview`: 4,795 orders, 18,470 lines, 120 chemists, 145 SKUs asked for and unavailable in 14 days, about 4.2 clerk minutes saved per order (an ESTIMATE, labelled).
- New endpoints. Each returns 200 with an honest note if `data/extended` is missing: `/api/overview`, `/api/backtest`, `/api/environment`, `/api/stockouts`, `/api/asha/history`.

## Gemini engineering (added 21 Nov, afternoon)

- Usage ledger and `GET /api/ai/usage`; "AI usage and cost" panel on /about; spend guard, per-IP rate limit, concurrency cap, jittered retries, cache-friendly prompt layout, per-job thinking levels. Measured about INR 0.25 per order read. Details: `docs/GEMINI_ENGINEERING.md`.

## Checks run

| Check | Result |
|---|---|
| Backend pytest | 120 passed (about 44 s) |
| Frontend tsc, eslint, vitest, build | all clean; 27 vitest tests |
| Axe (frontend round) | 0 violations, 9 routes, desktop and phone, light and dark |
| Playwright, 9 routes at 1440 and 390 (this pass) | 0 console errors, 0 horizontal overflow, one h1 per page; shots in `docs/qa_screens/final/` |
| Story via API on port 8120 | all 10 messages parsed, approve, duplicate 409, audit, 3 explanations, chemist send (text and voice), media round trip, two ASHA reports confirm the Kurla alert |
| Demo video | `docs/video/FirstSign_demo.mp4`, 136.1 s, 1920x1080 H.264 + AAC, 21.9 MB; 4 frames checked |
| Key leak | the first 12 characters of the key appear only in `.env` (git-ignored); not in dist, cache, state, logs or API responses |

## Measured numbers

- Parse of the 10 bundled messages, all from the warmed cache: 0.3 to 0.5 s each. All 10 are live Gemini results (gemini-3.5-flash, 3.8-flash, 3.1-flash-lite). msg_01 6 green; msg_02 5 green and 1 unknown (the children's syrup); msg_08, msg_09 and msg_10 fully green; msg_07 lists "Avil 25 - 5" as crossed out.
- Cold Gemini latency seen earlier today: msg_03 58 s; explanations 29 to 54 s.
- Back-test (SIMULATED scenario): median lead of the pharmacy signal over the official report 12 days, over the ASHA rise 2 days. One false alarm (citywide bad-air week, 5 pins) and one missed event (Dharavi typhoid) are shown honestly.
- Extended data: 14,331 orders and 56,042 lines, reconciled with history.csv.

## Fixed in this QA pass

- Cached explanations were keyed on live counts, so approving any order (for example msg_09) made all three miss. With Gemini failing (HTTP 402) the page then showed the plain data-only text. The last good Gemini explanation per alert is now saved (`backend/.cache/explain_last_<alert>.json`) and shown, labelled, when Gemini is down. Test added; verified after approving msg_01, msg_02 and msg_09.
- The alert page said "Explained by Gemini with Google Search" even with no sources. It now says "from our order data" unless the answer is grounded.
- Stale docs fixed: test count (120), the two-report ASHA rule, the msg_03 note.

## Known limits (honest)

- Gemini returned HTTP 402 for uncached requests between about 05:50 and 06:30 IST. The demo works from the warmed cache; anything new (a typed Hindi ASHA report, Regenerate, a new photo) needs a working key. Fallback: `DEMO_OFFLINE=1`, and say the results are replayed.
- Google Search grounding returns no sources on this key; explanations are not grounded and say so.
- `backend/.cache` is git-ignored. A fresh clone or a Cloud Run instance has no warm cache; run `python -m app.warm` with a working key there.
- Chemist-sent media is stored on local disk (ephemeral on Cloud Run).
- In the video the second ASHA report reuses the first sample audio (different ASHA and locality). The sample voice notes are silent in the video because screen capture has no audio.
- A pin with only zero-report days shows "no ASHA reports yet" in the history panel. The radar has no days-of-cover chip (it is in the reason text).
- ASHA reports filed live today extend the simulated history chart to 21 Nov.
- Firestore, BigQuery and the Docker image were never run. There is no Cloud Run URL yet.
- Free-tier models; the baseline is not clinically validated.

## How to run

```
bash run_local.sh        # http://localhost:8000   (DEMO_OFFLINE=1 for canned results)
```
