# FirstSign: submission checklist

Deadline: **9:00 AM IST, 21 Nov 2026**. Submit: working link, pitch deck (PDF, under 5 MB), optional pitch video, code base.

## Status

| Item | State | Note |
|---|---|---|
| Code base | Ready locally | 83 backend tests pass; frontend lint, tsc, vitest and build pass. Not yet pushed |
| Working link | **Not live** | Cloud Run deploy needs gcloud sign-in and billing; never run |
| Pitch deck | Content ready (`DECK.md`) | Slides not built; screenshots not yet in `docs/screens/` |
| Pitch video | Script ready (`PITCH_VIDEO_SCRIPT.md`) | Not recorded |
| Gemini cache | Warm for 9 of 10 inbox messages | Explain not cached with grounding |
| Grounded Google Search | **Not working on this key** | 429 on every model on the free tier |

## Do these in order

1. **Billing and key (blocks 2, 3, 4).** Enable billing on project `firstsign-buildathon`, or put a billed key in `.env`. This also lifts the 20 requests per day limit on the faster models and enables Search grounding.
2. **Check tests and a local run.**
   ```bash
   cd backend && python -m pytest -q
   cd ../frontend && npm run lint && npm test && npm run build
   cd .. && bash run_local.sh        # http://localhost:8000, stop with Ctrl+C
   ```
3. **Warm the cache** (with the billed key, so grounded explanations are stored):
   ```bash
   cd backend && python -m app.warm
   ```
   Then open each of the 3 alerts once in the officer page and press Explain.
4. **Deploy.**
   ```bash
   gcloud auth login
   bash infra/deploy.sh
   ```
   The script prints the live URL and checks `/api/health`. Then `curl -X POST <url>/api/demo/reset` and rehearse `DEMO_SCRIPT.md` once on the live link, on a phone.
5. **Screenshots.** Create `docs/screens/` and capture: landing, inbox with a parsed order, radar Kurla card, officer map, alert detail with explanation, ASHA phone record screen, About. Light theme, 1440 px and 390 px.
6. **Build the deck** from `DECK.md`, export PDF, check size is under 5 MB. Put the live URL and a QR on slide 1. If the dashboard shows a template, map the slides as noted at the top of `DECK.md`.
7. **Record the video** (2 minutes, `PITCH_VIDEO_SCRIPT.md`) from the live link. Upload to YouTube as unlisted, or a Drive link set to anyone with the link.
8. **Code base.** Confirm `.env` is not tracked (`git ls-files | grep -c "^.env$"` must print 0), then push the repo to a new GitHub repository for this competition. Make it public or add the organisers as viewers.
9. **Submit on the Hack2skill dashboard:** live link, deck PDF, video link, GitHub link. Open each link in a private window to confirm it works.
10. **Rotate the Gemini key after judging** and delete the Secret Manager version if it was a personal key.

## If the live link cannot be ready
Submit the GitHub link with the run command (`bash run_local.sh`), and demo from the laptop with `DEMO_OFFLINE=1` as the fallback. Label offline results as pre-recorded in the pitch. Do not present a localhost URL as the working link.

## Known issues to disclose, not hide
- Free-tier key: grounding returns no sources; the app says so.
- The Marathi sample (msg_03) times out on the slow model and falls back to a labelled pre-recorded sample.
- Signal evidence is simulated data. All demo history is labelled as simulated in the UI.
- Firestore and BigQuery paths are written but untested; the Docker image was not built in QA.
- `ARCHITECTURE.md` and README still say one ASHA report confirms an alert; the code now needs two.
