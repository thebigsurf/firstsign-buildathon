# How FirstSign uses Gemini (engineering one-pager)

Status key: **MEASURED** = recorded by our own usage ledger on live calls, 21 Nov 2026. **LIST** = read on Google's official page (linked below). **ESTIMATE** = our arithmetic or assumption.

## 1. Which model does which job

| Job (ledger key) | Model | Why | Thinking | Output |
|---|---|---|---|---|
| Voice note, photo or text to order lines (`parse_audio`, `parse_image`, `parse_text`) | `gemini-3.5-flash`, then `gemini-3.8-flash`, then `gemini-3.1-flash-lite` | One fast multimodal call transcribes and structures; no separate speech-to-text step | `minimal` (extraction, reasoning adds latency not accuracy) | JSON schema |
| ASHA voice report to counts (`asha_report`) | same chain | Counts only, short audio | `minimal` | JSON schema |
| Web search for causes (`explain_grounded`) | `gemini-4-hydrogen`, then `gemini-3.5-flash`, then `gemini-3.1-flash-lite` | Google Search grounding; sources come from grounding metadata, not from model prose | `low` | free text + sources |
| Explain the rise and draft actions (`explain_reason`) | same reasoning chain | Needs real reasoning over our numbers plus the findings | `medium` | JSON schema |

A human approves every order line the model is unsure of and every outbound action. Gemini never writes to the order book on its own.

Honest note on model names: `gemini-3.5-flash` serves our requests but is **not listed** on Google's pricing, models or thinking pages (they list `gemini-3.5-flash-lite`, `gemini-3.6-flash`, `gemini-3.8-flash`). We price it as `gemini-3.5-flash-lite` and flag it in the API (`listed_on_pricing_page: false`). `gemini-3.8-flash`, `gemini-3.1-flash-lite` and `gemini-4-hydrogen` are listed.

## 2. Measured tokens, time and cost per call

20 order calls (10 sample messages, run twice with our disk cache bypassed), 4 ASHA calls, 2 full explanations (grounded search + reasoning). Cost uses the list prices below at **1 USD = INR 90 (our assumption, env `USD_INR`)**. Raw rows: `docs/measure/run1.json`, `run2.json`.

| Input | n | Prompt tokens (avg) | of which audio | Served from cache | Output | Thinking | Time p50 / p95 | Cost each (INR) |
|---|---|---|---|---|---|---|---|---|
| Voice note to order | 8 | 8,109 | 433 | 69% | 730 | 0 | 5.0 s / 10.5 s | 0.25 (0.23 to 0.27) |
| Handwritten photo to order | 6 | 8,782 | 0 | 73% | 796 | 0 | 4.6 s / 6.1 s | 0.26 (0.25 to 0.28) |
| Typed message to order | 6 | 7,727 | 0 | 60% | 616 | 0 | 3.6 s / 4.3 s | 0.23 (0.19 to 0.33) |
| **All orders** | 20 | 8,196 | 173 | 68% | 716 | 0 | 4.6 s / 7.2 s | **0.25 (0.19 to 0.33)** |
| ASHA voice report | 4 | 560 | 351 | 0% | 152 | 0 | 2.5 s / 3.0 s | 0.05 |
| Explain: web search | 2 | 400 | 0 | 0% | 717 | 518 | 12.6 s / 13.1 s | 0.89 |
| Explain: reasoning | 2 | 2,901 | 0 | 0% | 1,254 | 1,982 | 18.0 s / 19.1 s | 2.58 |
| **One alert explanation** | | | | | | | about 31 s | **about 3.5** (once per alert, then stored) |

Findings, MEASURED:
- The prompt is dominated by the 160-item catalogue (about 6.9k tokens). We now send it inside the system instruction, ahead of the variable audio, photo or text, so Gemini's implicit cache can match the shared prefix. Across the two runs, **59% then 70% of all prompt tokens were billed at the cached rate**. Hits are best-effort (some calls hit, some do not), so the cost range is real, not noise.
- Trimming repeated aliases cut the catalogue table by 11% (16.5k to 14.6k characters) without removing any name a chemist can say.
- Photos use about 1,050 extra tokens at `media_resolution=high`. We tried `low` (about 230 image tokens): it saves about INR 0.02 per photo and risks handwriting accuracy, so we keep `high` (Google recommends `high` for most analysis; its default for Gemini 3 is the same 1,120 tokens).
- Audio costs 32 tokens per second (LIST), so a 13 s voice note is about 430 tokens; audio is a small share of an order's cost. The catalogue and the JSON answer are the cost.

**Against the deck's "INR 0.4 to 0.7 per order" (which includes human checking):** the AI alone measures **about INR 0.25 per order** (0.19 to 0.33). That leaves INR 0.15 to 0.45 for human checking and overhead, so the deck's range holds, with the AI the smaller part. It is sensitive to the model: the same orders on `gemini-3.8-flash` would cost about INR 0.46 (ESTIMATE from list prices and the measured tokens), and with no cache hits at all INR 0.38 on our priced model or INR 0.80 on 3.8 Flash. Note `gemini-3.8-flash` list prices double on 1 Jan 2027 (LIST).

## 3. Limits, throttling and protection (all in the code, all tested)

| Protection | What it does | Where |
|---|---|---|
| Concurrency cap | A process-wide semaphore (`GEMINI_MAX_CONCURRENCY`, default 4). A burst queues instead of hitting the quota; queue time is recorded per call. | `gemini.py` |
| Per-IP rate limit | 60 requests per minute per client on order parse, chemist send, ASHA report and explain (`RATE_LIMIT_PER_MIN`; the code default is 20, the deploy sets 60). Over the limit: HTTP 429, a friendly message, `Retry-After`. Uses the last `X-Forwarded-For` entry, which Cloud Run appends and a client cannot spoof. | `ratelimit.py`, `api.py` |
| Retry with jitter | Retries 408/429/5xx, never 400/403 (matches Google's guidance). Honours the server's `Retry-After` header and RetryInfo, adds jitter, gives up on a model whose quota window is longer than 45 s and moves to the next model. A shared deadline caps the whole chain. | `gemini.py` |
| Daily cost guard | `DAILY_GEMINI_BUDGET_INR` (default 300). Past it, no new Gemini call is made; saved answers still serve, and known samples return the labelled pre-recorded result. The ledger resets at midnight IST. | `usage.py`, `gemini.py` |
| Request size | Upload read capped at 20 MB + 1 byte, whole request capped at 25 MB (413), text capped at 4,000 characters, file signature checked before any call is spent. | `api.py`, `main.py`, `parsing.py` |
| Output cap | `max_output_tokens` per job (8,192 for parse and explain, 4,096 for ASHA) so a runaway answer cannot burn money. | `gemini.py` |
| Honest fallbacks | Every fallback is labelled in the UI (`offline-sample`, `data-only-fallback`) and counted in the ledger. | `parsing.py`, `agent.py` |

Cloud Run: concurrency defaults to 80 requests per instance (LIST). Our requests are I/O-bound waits on Gemini, so the default suits us; the semaphore, not Cloud Run, is the throttle.

## 4. Caching

- **Disk cache** keyed by sha256 of model, prompt, system, schema, thinking level and media bytes: a repeated input costs nothing and answers in about 0.4 s.
- **Implicit cache (Gemini):** on by default for 2.5 and newer. Google's page lists a 4,096-token minimum for Gemini 4 and 3.8 Flash and 2,048 for 2.5; the minimum for `gemini-3.5-flash` is not published, but MEASURED hits start at about 5k cached tokens, which our 6.9k-token catalogue prefix clears. Hits are best effort.
- **Explicit cache: not used, on purpose.** The docs say it is unavailable for Gemini 4 and for the Interactions API; our prefix is small, storage is billed per hour, and implicit caching already gives the discount without a cache object to expire. We would revisit with a larger, fixed prompt and steady traffic.

## 5. Failure modes and what the user sees

| Failure | Behaviour |
|---|---|
| Model busy (503) or quota (429) | Backoff with jitter, then next model in the chain. |
| Every model fails on a known demo sample | Labelled pre-recorded reading; background thread keeps retrying so the next parse is live. |
| Every model fails on a new input | Clear 502 message; nothing is invented. |
| Search grounding over quota | Skipped for 5 minutes; the explanation still returns from our data, with "No external sources found". |
| Reasoning call fails | Last good explanation for that alert, else a data-only explanation, both labelled. |
| Budget used up | As above, plus a notice on the About page. |
| Junk or oversized file | 400/413 before any Gemini call. |

## 6. What we would do at scale

- Vertex AI with **Provisioned Throughput** for predictable latency and quota, and regional endpoints near Mumbai.
- The **Batch API** for back-fills and nightly re-scoring (Google lists batch limits per tier; about half price on the models whose batch prices we saw, our calculation, not a stated discount).
- Move the rate limit to **Cloud Armor** or an API gateway and the ledger to **BigQuery**, with alerts on cost per order.
- Use the **Files API** only above 20 MB inline requests (voice notes are well under).
- Re-measure when model prices change and set `GEMINI_MODEL_FAST` by cost per correct order, not by name.

## 7. Observability

`GET /api/ai/usage` returns totals, per-job and per-model averages, cache hit rate, fallback rate, error rate, p50/p95 latency, cost per order, today's spend against the budget, and the price table with the assumed exchange rate. The About page shows it in plain English. `python -m app.measure` reproduces the table above (it spends real money: about 14 calls plus 2 per explanation).

## Sources (read 21 Nov 2026)

- Pricing: https://ai.google.dev/gemini-api/docs/pricing (redirects to https://aistudio.google.com/docs/pricing). Used: `gemini-3.8-flash` USD 0.75 in / 3.75 out / 0.075 cached through 31 Dec 2026; `gemini-3.1-flash-lite` USD 0.25 in (0.50 audio) / 1.50 out / 0.025 cached; `gemini-4-hydrogen` USD 1.50 / 7.50 / 0.075; `gemini-3.5-flash-lite` USD 0.30 / 2.50 / 0.03 (proxy); Search grounding 5,000 free per month then USD 14 per 1,000. `gemini-3.5-flash` is not on the part of the page we could read.
- Context caching: https://aistudio.google.com/docs/caching
- Rate limits (per project, RPM/TPM/RPD, tiers, batch limits): https://aistudio.google.com/docs/rate-limits
- Thinking levels: https://aistudio.google.com/docs/thinking
- Audio (32 tokens per second, 20 MB inline total, Files API above that): https://aistudio.google.com/docs/audio
- Media resolution (low 280, medium 560, high 1,120 tokens per image on Gemini 3 and 4): https://aistudio.google.com/docs/media-resolution
- Token counting (usage fields): https://aistudio.google.com/docs/tokens
- Troubleshooting and retry guidance (429/503, backoff with jitter, do not retry 400/403): https://aistudio.google.com/docs/troubleshooting
- Model list and status: https://aistudio.google.com/docs/models
- Cloud Run concurrency: https://docs.cloud.google.com/run/docs/about-concurrency
