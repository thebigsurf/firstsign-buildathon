# FirstSign: release notes (QA certification, 21 Nov 2026)

All data in the product is simulated and labelled as such. No real patient names.

## What was verified today

- Backend: `python -m pytest -q` gives 83 passed.
- Frontend: `npm run build`, `tsc --noEmit`, `eslint` and `vitest` (4 tests) all pass.
- Live run (real Gemini key, port 8050) and offline run (`DEMO_OFFLINE=1`) of the full path: inbox parse, approve, audit, radar, officer alert, explain, approve actions, ASHA visit list, ASHA voice report, alert confirmation.
- Playwright screenshots of every route at 1440 and 390 wide, light theme, clean state: no console errors, no horizontal scroll on any route.

## Fix verification

| Finding | Result |
|---|---|
| F1 chain | Confirmed. Parse, ASHA and explain run live on gemini-3.1-flash-lite (explain also seen on gemini-3.5-flash). Partial: fast models still quota-limited on this key. |
| F2 Devanagari | Confirmed. msg_02 live: 5 green, 1 unknown, no nonsense reasons. |
| F3 offline story | Confirmed. All 10 messages match their expected files exactly. |
| F4 silent matches | Confirmed. "pan 20 patta" and "crosin 30" are uncertain with reasons. New related gap: see open issues. |
| F5 dropped line | Not reproducible (msg_03 never completes live). Warning exists. |
| F6 bad media | Confirmed. Random bytes, text-as-mp3 and html-as-jpg return 400 `invalid_media`. |
| F7 grounding | Still open. No grounded sources in any run. UI says so honestly. |
| F8 duplicate and cross-pin | Confirmed. Duplicate gives 409, wrong pin gives 422. |
| F9 report swing | Confirmed. One report: 0.594 to 0.799, stays open. Second report: 0.915, confirmed. |
| UX-1 to UX-9 | UX-1 (no overflow at 390 and 1440, all routes), UX-3, UX-8, UX-9 confirmed visually and by script. UX-2, 4, 5, 6, 7 accepted from the fixer's DOM checks; axe was not re-run. |

## Measured numbers (today, live key)

- Parse accuracy on the 10 bundled messages: 55 of 56 expected lines placed on the right SKU (98.2%). The one miss is the deliberate unknown "children's syrup" line.
- Silent wrong greens: 1 (msg_07, a crossed-out line was read as an order; see open issues).
- Parse latency, uncached: text 5.1 s, photo 3.7 s, voice 11.8 s. Cached: about 0.2 s.
- ASHA voice report: 3.3 s. Explain with agent: 29 s live (74 s seen earlier), 0.1 s cached.
- Telemetry after the run: 4 live calls, all on gemini-3.1-flash-lite, p50 4.1 s, p95 11.4 s.
- Metrics strip after one approval: edit rate 20%, unknown 7.1%, 1 decoy suppressed (Ghatkopar West, 3.4x volume but 0% breadth).

## Known limitations (honest)

- Google Search grounding returned no sources on this key. The explanation falls back to order data only and says "No outside sources found". The 20% Google AI criterion would be much stronger with a billed key.
- Marathi voice note (msg_03) hangs about 186 s on Gemini 504s, then falls back to the labelled pre-recorded sample.
- Time to confirm an alert now needs two ASHA reports. `ARCHITECTURE.md` and `DEMO_SCRIPT.md` still say one report confirms.
- Free-tier models are used. Deploy with a billed key.
- Full-page phone screenshots show the fixed bottom bars mid-page; use viewport shots for the deck.
- Simulated history and chemists; baseline is not clinically validated.

## How to run

```
cd frontend && npm ci && npm run build
cd ../backend && python -m uvicorn app.main:app --port 8000
# offline: set DEMO_OFFLINE=1 first
```

## Pending submission items

- Cloud Run URL: not deployed by QA. Needs billed key in Secret Manager, `python -m app.warm`, then the infra script.
- Pitch deck (docs/DECK.md is the source) and optional video.
- Code repository link (the new GitHub folder, tech lead commits).
- Screens for the deck: `docs/screens/` (landing, inbox, inbox_hindi_voice, radar, officer, alert, alert_explained, asha, about; desk and phone).
