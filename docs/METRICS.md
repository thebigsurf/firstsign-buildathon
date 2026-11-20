# FirstSign: success metrics

*Head of Product. "Live" = computed from actual use and shown in the app (`/api/metrics`, officer and about pages). "Est." = assumption, labelled as such in the UI. Demo figures come from simulated data and samples; pilot targets are goals, not results.*

## 1. Live metrics shown in the product

| Metric | Definition | Where shown | Demo target | Notes |
|---|---|---|---|---|
| Lines auto-matched % | Lines with status `matched` / all parsed lines | Inbox header, About | >= 80% on samples | `/api/metrics.auto_matched_pct` |
| Uncertain % | Lines `uncertain` / all lines. Shown, never hidden | Inbox header | 10-20% | Healthy: honest abstention beats confident error |
| Unknown % | Lines `unknown` / all lines | Inbox header | < 5% | Red lines; clerk must resolve |
| Parse latency | Median and p95 of `latency_ms` per message | Inbox header | median < 6 s | `avg_latency_ms` exists; ask for p50/p95 (see CONTRACT_REQUESTS) |
| Clerk edit rate | Approved lines changed by the clerk / lines approved | Audit page | < 15% | Needs original-vs-approved stored |
| Clerk minutes saved per order (est.) | (manual minutes per order) - (review minutes). Manual est. 3 min per 10-line order incl. phone calls; review est. 0.5 min. Shown as "est." | Inbox header | ~2.5 min per order | Assumption, to be replaced by timed pilot |
| Alert precision | confirmed / (confirmed + dismissed) among alerts with at least one ASHA report | Officer page | n/a in demo (few reports); shown as "n reports" | Only computed once ASHA reports exist |
| Days from first sign to action | Alert `started` to first approved action | Alert page | demo: seeded 6-day rise, action same session | Compare to the days the rise ran before we flagged it |
| Alerts raised / decoys suppressed | Count of alerts; count of high-volume low-breadth cells not alerted | Officer page | 1 decoy suppressed | Shows false-alarm discipline |
| Gemini usage | Calls, models used, fallback count, grounded sources per explanation | About page | visible | Supports the Google AI depth criterion |
| ASHA reports | Number structured; confirmations vs cancellations | Officer page | seeded + live | Ground-truth growth |

## 2. Pre-demo quality gates (internal)

| Gate | Target |
|---|---|
| Parsing accuracy on the sample set (sku match vs `.expected.json`) | >= 85% lines correct, 0 silently wrong (wrong ones must be uncertain) |
| Signal back-test on seeded history | Both seeded events alert; decoy and respiratory bump behave as designed; 0 false alerts on quiet pin codes |
| Offline mode | Every demo step completes with `DEMO_OFFLINE=1` |
| `pytest` | Green |

## 3. North-star metrics for a pilot (estimates, to be proven)

| Metric | Pilot target (est.) | Why |
|---|---|---|
| Weekly active order desks | 5 distributors in 90 days | Proves daily use |
| Share of a distributor's orders flowing through FirstSign | >= 50% | Proves it replaces typing, not duplicates it |
| Clerk time on order entry | -40% (est.) | The thing the owner pays for |
| Wrong-item dispatches | -30% vs prior 90 days (est.) | Money saved |
| Alert precision (confirmed by ASHA/field visit within 7 days) | >= 50% initially, rising | Brazil's best large low- and middle-income study had 48% precision; matching it with ground truth is a fair first bar |
| Lead time: first FirstSign flag vs first official/hospital record | Report median and spread, including cases of no lead | Honest: lead is a hypothesis, not a claim |
| False alerts per pin code per month | < 1 | Alert burden decides whether officers trust it |
| ASHA report completion within 48 h of an approved visit list | >= 70% | Closes the loop |
| Labelled ground-truth reports collected | 200 in 90 days | Fuel for the medicine-to-illness mapping |
| Retrospective back-test | 5-10 known outbreaks, pre-registered rule, precision and lead published | The study a sceptical epidemiologist will ask for |

## 4. How we will be wrong (tracked, not hidden)

Advisories, price changes, schemes and panic buying move sales without illness. We track bulk-buy decoys now; an event calendar is pilot work. Diarrhoea medicines have the weakest evidence for a lead; respiratory and fever are the better first targets, and we report each group separately.
