# Wake-up note (21 Nov 2026)

## What was built overnight
FirstSign now has a chemist send screen, an extended simulated dataset (14,331 orders, ASHA reports, official cases, stock, plus real weather and air), a smarter stock radar with stock-outs, a simulated back-test that shows a false alarm and a missed event honestly, ASHA history, landing tiles, crossed-out line handling, a 2:16 demo video, 120 passing backend tests and clean frontend checks.

## Run it in one command
```
bash run_local.sh        # http://localhost:8000   (add DEMO_OFFLINE=1 if Gemini fails)
```

## Check first
Gemini returned HTTP 402 on new requests this morning. Run `cd backend && python -m app.warm`. If it ends with "live-cached" for everything, you are fine. If not, the demo still works from the saved cache, but anything new (typed ASHA text, Regenerate) will not.

## Five things before 9 AM
1. Fix billing or the key, then re-run `python -m app.warm`.
2. `gcloud auth login`, then `bash infra/deploy.sh`; open the link on your phone.
3. Push the repo (check `.env` is not tracked); make it public or add the judges.
4. Build the deck PDF from `docs/DECK.md` (screens in `docs/screens/`), under 5 MB.
5. Upload `docs/video/FirstSign_demo.mp4`, then submit all four links.

Details: `docs/SUBMISSION_CHECKLIST.md` and `docs/RELEASE_NOTES.md`.
