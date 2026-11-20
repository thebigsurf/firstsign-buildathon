# FirstSign backend

FastAPI service for the order desk, the demand signal and the ASHA loop. The contract is `../ARCHITECTURE.md`; additions are listed at the end of `../docs/CONTRACT_REQUESTS.md`.

## Run

```bash
cd backend
python -m pip install -r requirements-dev.txt
# put GEMINI_API_KEY in ../.env (never commit it)
python -m uvicorn app.main:app --port 8001
```

- `GET /api/health` shows the models and whether it is in offline mode.
- With the frontend built (`../frontend/dist`), the same port serves the app at `/`. Without it, `/` returns a JSON note.
- `DEMO_OFFLINE=1` (or no key) serves canned answers from `data/samples/*.expected.json`, so the demo never dies. The UI must show the offline badge (`/api/health.offline`).

## Test

```bash
python -m pytest                      # 70+ tests, no network, about 1 minute
python -m tests.eval_parsing          # live Gemini against data/samples; prints accuracy and silent errors
```

## Settings (environment)

| Variable | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | none | Missing key means offline mode |
| `GEMINI_MODEL_FAST` | `gemini-3.5-flash,gemini-3.8-flash,gemini-3.1-flash-lite` | Parsing chain, first that answers wins |
| `GEMINI_MODEL_REASON` | `gemini-4-hydrogen,gemini-3.5-flash,gemini-3.1-flash-lite` | Agent chain |
| `DEMO_OFFLINE` | `0` | Force canned answers |
| `STORAGE` | `local` | `firestore` needs `google-cloud-firestore` |
| `SIGNAL_BACKEND` | `local` | Reported by health; the BigQuery path is `app/bq.py` (see its docstring) |
| `DEMO_AS_OF` | last day of history | Pin "today" to an earlier date |
| `RADAR_COVER_DAYS` | `5` | Days of cover in stock radar quantities |
| `ALLOW_DEMO_RESET` | `1` | `0` disables `POST /api/demo/reset` |

Runtime files, both git-ignored: `.cache/` (Gemini responses keyed by sha256 of model, prompt and media) and `.state/state.json` (orders, audit, ASHA reports, approvals, so a restart keeps the demo state).

## Layout

| File | Job |
|---|---|
| `app/main.py` | App factory, request ids, JSON logs, error shape, static frontend with SPA fallback |
| `app/api.py` | Routes only |
| `app/service.py` | Inbox, parse, order approval, audit, ASHA loop, action approval, metrics |
| `app/gemini.py` | One client: fallback chain, backoff, timeouts, disk cache, telemetry, offline samples |
| `app/parsing.py` | Voice, photo and text order parsing; ASHA report parsing; offline readers |
| `app/catalogue.py` | Exact, fuzzy and phonetic matching; status, confidence and alternatives per line |
| `app/signal.py` | Baselines, breadth, co-movement, alert clusters, confidence, ASHA update, stock radar |
| `app/agent.py` | Grounded search, then reasoning with our data; drafts the three actions |
| `app/store.py` | Seed data loader, `LocalStore` (default) and `FirestoreStore` |
| `app/bq.py` | Optional BigQuery export and AI.FORECAST baseline |

## Design for blame, in the code

- Every parsed line carries `status`, `confidence`, `alternatives` and a plain-words `reason`. Nothing is silently corrected: a disagreement between Gemini and the catalogue makes the line `uncertain`.
- `POST /api/orders` diffs the approved lines against the AI reading and writes one audit entry per edit, addition, removal and accepted uncertain line, each with before and after.
- No outbound action exists without `POST /api/actions/approve`, which stores the draft, the approved text and who approved it.
