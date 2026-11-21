# FirstSign: submission checklist

Deadline: **9:00 AM IST, 21 Nov 2026**. Submit: working link, pitch deck (PDF under 5 MB), optional video, code base.

## State at about 06:40 IST

| Item | State |
|---|---|
| Code | Ready. 135 backend tests; frontend tsc, lint, 41 vitest and build pass. Not pushed (no git was run overnight) |
| Working link | NOT live. Needs billing, gcloud login and deploy |
| Deck | Source is `docs/DECK.md`; new screenshots are the numbered files 01 to 11 in `docs/screens/`. Slides not built |
| Video | Done: `docs/video/FirstSign_demo.mp4` (2:16) and `FirstSign_demo_captions.srt` |
| Gemini | Cache warm for all 10 messages and 3 alerts. Live calls returned HTTP 402 this morning |

## Do these in order

1. **Fix billing or the key (5 min).** Enable billing on project `firstsign-buildathon`, or put a billed key in `.env`. You will see whether it works in step 2.
2. **Re-warm and check locally.**
   ```bash
   cd backend && python -m pytest -q && python -m app.warm
   cd .. && bash run_local.sh     # http://localhost:8000
   ```
   `warm` should end with "live-cached" for 10 messages and 3 alerts and "fallback ...: none". If the key still fails, keep the existing cache and demo with `DEMO_OFFLINE=1`.
3. **Sign in to gcloud and deploy.**
   ```bash
   gcloud auth login
   gcloud config set project firstsign-buildathon
   bash infra/deploy.sh
   ```
   The script prints the URL and checks `/api/health`. The warm cache is git-ignored, so a clean build has none: copy `backend/.cache` into the build or run `python -m app.warm` with the deployed settings. Then `curl -X POST <url>/api/demo/reset` and open the link on a phone.
4. **Code base.** Confirm `.env` is not tracked (`git ls-files | grep -c "^.env$"` must print 0). Push to a new GitHub repository. Make it public, or add the organisers as viewers.
5. **Deck.** Build the slides from `docs/DECK.md`, export a PDF under 5 MB. Put the live URL and a QR on slide 1. Screenshots: `docs/screens/` (numbered) or `docs/qa_screens/final/`.
6. **Video.** Upload `docs/video/FirstSign_demo.mp4` to YouTube (unlisted) or Drive (anyone with the link). Delete `docs/video/raw`, `build`, `frames` and `audio` before pushing (about 40 MB of intermediates).
7. **Submit** on the dashboard: live link, deck PDF, video link, GitHub link. Open each link in a private window.
8. **After judging:** rotate the Gemini key.

## If the live link cannot be ready
Submit the GitHub link, the video and the run command (`bash run_local.sh`). Say plainly that the demo is not hosted. Do not present localhost as the working link.

## Disclose, do not hide
- All history, ASHA, official-case and lab data are simulated; the back-test is a simulated replay; weather and air are real.
- No Google Search grounding sources on this key.
- Firestore, BigQuery and Docker were not exercised.
- The video's second ASHA report reuses the first sample audio.
