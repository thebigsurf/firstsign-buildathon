
## From Head of Product: rubric gap review of ARCHITECTURE.md (20 Nov 2026)

Each item is the simplest compatible addition. P1 = needed for the demo path or a rubric criterion; P2 = nice to have.

### Functional (30%)
1. **P1 Demo reset and ASHA list.** Add `POST /api/demo/reset` (reload seed, clear approvals) and `GET /api/asha` (list ashas with pin) so the demo can be rerun and the ASHA picker works.
2. **P1 Alert detail and status rule.** Add `GET /api/alerts/{alert_id}`. Define status transitions: `confirmed` when confidence >= 0.7 and at least one ASHA report is above background; `dismissed` when two reports are near zero. State this in `signal.py` docstring and show it in the UI.
3. **P1 Audit schema.** Define `AuditEntry {id, ts, actor, kind: order_approved|line_edited|action_approved|asha_report, ref_id, before, after}`. `POST /api/orders` must receive both original parsed lines and approved lines so edits can be logged and an edit rate computed.
4. **P1 Offline badge.** `/api/health.offline` must drive a visible "Offline demo mode" badge in the UI so judges are never misled that canned results are live Gemini.

### Technical architecture (20%)
5. **P1 Eval harness.** Add `backend/tests/eval_parsing.py` (or a pytest marker) that scores parsing against `data/samples/*.expected.json` and prints line accuracy and silent-error count. Feeds METRICS.md quality gates.
6. **P1 Signal back-test.** A test asserting both seeded events alert, the decoy does not, and quiet pins stay normal.
7. **P2 Request ids and structured logging** (request id, model used, fallback count, latency) in `gemini.py`.
8. **P2 Secrets.** Deploy script reads the key from Secret Manager, not an env literal.

### Google AI depth (20%)
9. **P1 Telemetry endpoint.** Add `GET /api/telemetry`: `{calls, by_model, fallbacks, avg_latency_ms, grounded_sources_total, cache_hits}`. Show it on `/about` so judges see Gemini usage depth.
10. **P1 Grounding metadata.** Agent response `sources` must come from Gemini grounding metadata (real URLs), not model-written text. Add `search_queries: [string]` to the response.
11. **P2 Embeddings.** Use `gemini-embedding-001` as a catalogue-matching tiebreaker for `unknown` lines (fuzzy first, embeddings second), cached at startup.
12. **P2 Gemini text-to-speech** for the ASHA read-back (optional; skip if time is short).

### Problem-solution (15%)
13. **P1 Uncertainty reason.** Add `OrderLine.reason: string|null` (for example "two products sound like 'pan dee'") so yellow and red lines explain themselves. Core to design for blame.
14. **P1 Decoy visibility.** `/api/alerts` or `/api/signal` should expose suppressed cells (`suppressed: [{pin, group, ratio, breadth, why}]`) so the UI can show "high volume, low breadth, not alerted".
15. **P2 Event-aware baseline note.** Document that advisories and schemes move sales (evidence audit B3); optional `data/events.csv` to annotate the baseline.

### Metrics support (see METRICS.md)
16. **P1 Extend `/api/metrics`:** add `unknown_pct`, `latency_p50_ms`, `latency_p95_ms`, `edit_rate_pct`, `minutes_saved_est` (assumptions as constants in `config.py`: manual 3.0 min and review 0.5 min per 10-line order), `alert_precision` (null until reports exist), `reports_confirming`, `reports_cancelling`, `decoys_suppressed`, `days_first_sign_to_action`.

### UX and accessibility (10%)
17. **P2 Language toggle** EN/HI for static UI labels; ASHA view labels also in Marathi.
18. **P2 Empty, loading and error states** for every route; audio playback of the uploaded voice note beside its transcript so the clerk can check the transcript.

### Innovation (5%)
19. **P2 Closed loop made visible.** On the alert page show a timeline: first sign -> approval -> ASHA report -> confirmed, with day counts. This is our differentiator and costs little.

## From Frontend (21 Nov 2026)

1. **Visit list order.** The officer can reorder or remove localities before approving. `POST /api/actions/approve` for `asha_visit_list` now also receives `visit_list: [{locality_id, name, landmark, priority, reason}]` in the approved order, plus `edited_text` describing it. Please use `visit_list` instead of the stored draft when present.
2. **ASHA corrections.** No confirm or edit endpoint exists. When an ASHA corrects a tile, the app sends a second `POST /api/asha/report` with text starting "Corrected figures:". Suggest `POST /api/asha/report/{report_id}/confirm` with the corrected counts so one visit counts once.
3. **Audit and approvals.** The UI reads past action approvals from `/api/audit` (`kind=action_approved`, `detail.action`, `detail.approved_text`). A `GET /api/alerts/{id}/approvals` would be cleaner.
4. **Not used by the UI:** `not_available` is kept client-side only; `POST /api/orders` receives approved lines plus `original_lines`.

---

## From Backend: what was built against the requests above, and additions (20-21 Nov 2026)

All changes are additive to `ARCHITECTURE.md` section 5. Where a request was ambiguous the simplest compatible option was chosen.

### Request status

| # | Request | Status |
|---|---|---|
| 1 | `POST /api/demo/reset`, `GET /api/asha` | Done. Reset clears orders, parses, audit, ASHA reports, explanations, approvals and the parse log (local store only). Set `ALLOW_DEMO_RESET=0` to disable. Explanations are cached on disk (`backend/.cache`), so re-running the agent after a reset is instant. |
| 2 | `GET /api/alerts/{id}`, status rule | Done. `confirmed` = confidence >= 0.70 and at least one ASHA report above the background rate. `dismissed` = two or more near-zero reports and none above background. Stated in the `signal.py` docstring. Each alert carries `reasons[]`, `reports[]` (with `effect`: raised / lowered / neutral) and `base_confidence`. |
| 3 | Audit schema | Done with HoP's names: `AuditEntry {id, ts, actor, approved_by (same as actor), kind, ref_id, summary, before, after, detail}`. Kinds: `order_approved`, `line_edited`, `line_added`, `line_removed`, `uncertain_accepted`, `action_approved`, `asha_report`. `POST /api/orders` accepts optional `original_lines`; if omitted, the stored parse for that message is used. |
| 4 | Offline badge | `GET /api/health` returns `offline: true` when `DEMO_OFFLINE=1` or there is no key. Parsed results also carry `model` (`offline-sample`, `offline-rules`, or the Gemini model name). |
| 5 | Eval harness | `backend/tests/eval_parsing.py` (live Gemini against `data/samples`). Results in `backend/RUN_LOG.md`. |
| 6 | Signal back-test | `tests/test_signal.py::test_backtest_on_seed_data`. |
| 7 | Structured logging | JSON logs with request id; Gemini calls log model, attempt and latency. |
| 9 | `GET /api/telemetry` | Done: `{calls, by_model, fallbacks, errors, avg_latency_ms, grounded_sources_total, cache_hits, offline}`. |
| 10 | Grounding metadata | Done. `sources` come only from the response's grounding metadata; `search_queries[]` added. `grounded` and `search_note` say plainly when nothing was found. |
| 11, 12 | Embeddings, TTS | Not built (P2). |
| 13 | `OrderLine.reason` | Done (the field is named `reason`). |
| 14 | Decoy visibility | Done: `GET /api/signal` returns `suppressed: [{pin, area, group, ratio, breadth, why}]`. Each cell also has `flags` (`concentrated_volume`, `promoted_by_neighbour`). |
| 16 | Metrics | Done: all fields requested, plus `alerts_raised`. Time-saving constants are in `config.py`. `alert_precision` is `null` until a decided alert has a report. |

### Additions (frontend may use; none are required)

- `POST /api/orders/parse` also accepts only `message_id` (no file, no text): it reads that inbox message's sample from `data/`. `chemist_id` then defaults to the message's chemist.
- `GET /api/inbox/{message_id}/media` streams the sample audio or image so the UI can play it next to the transcript.
- `GET /api/inbox` items carry `status` (`new|parsed|approved`), `parsed` (last `ParsedOrder` or null), `order_id`, and a small `chemist` block.
- `GET /api/alerts/{id}`, `GET /api/localities?pin=`, `GET /api/asha`, `GET /api/telemetry`, `POST /api/demo/reset`.
- `POST /api/agent/explain` accepts `refresh: true` to recompute. Responses add `grounded`, `cached`, `search_note`, `search_queries`.
- `GET /api/asha/visits` returns a plain list, ranked 1..n, each item `{locality_id, name, landmark, priority, reason, pin, alert_id, group, group_label, approved_by, approved_at, reported}`. `reported` flips to true once that ASHA has filed a report for the locality.
- `POST /api/asha/report` returns the structured report plus `report_id`, `alert_id` (the alert it moved most), `new_confidence`, and `updates[]` (every alert in that pin code: old and new confidence and status).
- `/api/alerts` items: `asha_reports` is a count; the detail is in `reports[]`. Also `pin_details[]` (area, ratio, breadth per pin), `group_label`, `z`.
- `POST /api/orders` returns 400 with code `line_without_sku` if any line has no catalogue item; the clerk must pick one or remove the line. 409 if the message already has an approved order.
- Every error is `{"error": {"code", "message", "request_id"}}` and every response has an `X-Request-ID` header.

### Contract choices worth knowing

- **Demo clock.** "Today" is the last day in `history.csv` (19 Nov 2026), not the wall clock, so the seeded story always shows. Approved live orders add to that day.
- **Breadth.** History stores how many chemists ordered a group per day, not which. Breadth is therefore the share of the pin's not-yet-ordering chemists who are now ordering. One shop bulk-buying scores near 0.
- **Parsing latency.** Voice parsing is 5 to 45 s on the free tier depending on load (see `backend/RUN_LOG.md`). The UI should show progress, and parsed results are cached on disk by content hash, so a second parse of the same file is instant.
- `gemini-2.5-flash` returns 404 for this key (retired for new users); the chain skips it automatically.
