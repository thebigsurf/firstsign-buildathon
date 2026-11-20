# FirstSign: product

*Head of Product. 20 Nov 2026. Contract: `ARCHITECTURE.md`. Business numbers are estimates unless sourced.*

## 1. The problem, in three views

**The order clerk is drowning.** A medicine distributor (stockist) serves ~300-400 chemists. Orders arrive as WhatsApp voice notes ("bhaiya, 10 pan dee, 5 Dolo, woh bachchon wali syrup") and photos of torn, handwritten lists. A clerk types 80-120 lines a day into billing software, phones chemists to settle brand doubts, and takes the blame when a wrong item ships.

**The owner is blind.** He stocks by gut. He is long on one thing and out of another, and eats expiry losses. He has no view of what his chemists are suddenly buying more of.

**The health system sees illness late.** Much care is informal and never reaches surveillance. One signal of the gap: in 2023, medical death certificates recorded 3,254 dengue deaths while programme surveillance recorded 485 (different definitions, but the gap is 6.7x). Chemists see the first sign: people buy ORS and fever tablets before they show up at a hospital.

## 2. Users and jobs to be done

| Role | Job to be done | What FirstSign gives | What they fear (design answer) |
|---|---|---|---|
| **Order clerk** (Aman) | Turn today's voice notes and photos into a correct bill, fast, without blame | Parsed lines with confidence; yellow = unsure, red = unknown; last-order hint; one-click approve | "A mistake gets pinned on me." Every edit and approval is logged with the model's original reading, so blame is traceable and fair. |
| **Distributor owner** (Sunil) | Stock the right things before chemists run out; cut clerk time | Stock radar: "stock up on these, here is why", per pin code | "Tool leaks my chemist list." Chemist data stays inside his account; no cross-distributor sharing. |
| **Health officer** (ward/district) | Decide where ASHA workers go tomorrow | Ranked list of areas, a plain-language reason, a drafted visit list to approve | "False alarms waste my team." Alerts show breadth and confidence; the decoy case does not fire; precision is reported. |
| **ASHA worker** | Visit the right lanes and report in 30 seconds, in her language | Approved visit list on her phone; she speaks her observations; Gemini structures them | "More paperwork." Voice only, no typing, counts not names. |

## 3. The loop

1. **Orders pass through.** Clerk approves orders; counts per pin code and medicine group update live.
2. **Signal.** Each pin code and group is compared with its own baseline. A rise counts only if many chemists move together (breadth), not one bulk buyer.
3. **Explain.** A Gemini agent, using Google Search grounding plus our own counts, says why the area may be rising and drafts three actions: distributor note, officer note, ASHA visit list.
4. **Human approves.** Nothing goes out without a named person approving. Approvals are audited.
5. **ASHA reports.** Her voice note confirms or cancels the alert and is stored as labelled ground truth.
6. **Learn.** Confirmed and cancelled alerts teach which medicine groups really point to which illness, locality by locality.

## 4. Scope for the demo (Mumbai round)

**In:** voice and photo order parsing with confidence and catalogue match; clerk review and approval; audit log; signal and alerts on 90 days of simulated history with seeded events; stock radar; officer map, agent explanation, approval; ASHA mobile flow with voice report; live metrics; offline fallback so the demo never dies.

**Out:** billing-software write-back (Marg integration is the first post-pilot item), real payments, user accounts and login, multi-distributor tenancy, push notifications, the Dischargely product.

## 5. Real vs simulated

| Real | Simulated (labelled in the UI as "Simulated history for demo") |
|---|---|
| Gemini parsing of audio and images (live calls) | 90 days of order history, chemists, pin-code counts |
| Catalogue matching, signal maths, confidence update | The Kurla/Sion outbreak and its ASHA reports |
| Agent reasoning and Google Search grounding | Chemist and ASHA first names; sample voice notes and photos |
| Audit trail, metrics computed from actual use | Business pricing in the deck (estimates) |

No real patient names anywhere. Sample audio and handwriting are produced for the demo and marked as such.

## 6. Data and privacy rules

- Orders store chemist ID, pin code, items and time only. No patient names.
- ASHA reports store counts, not names.
- Audio and images are processed in memory and dropped after the request (demo samples excepted).
- Every AI output is shown with its uncertainty. Nothing is silently corrected; edits are logged as original vs approved.
- A human approves every outbound action; the approver's name and time are logged.
- Alerts name areas (pin code, locality), never individuals.

## 7. Business model, in plain words

- **Distributors pay monthly.** Our estimate: Rs 3,000-4,500 per distributor per month, because it frees part of a clerk's day. One parsed order costs us roughly Rs 0.4-0.7 (most of it human checking). Estimate, not yet tested with a customer.
- **Public-health side is grant-funded.** District pilots at roughly Rs 25 lakh to 2 Cr each, funded by health missions, foundations or research grants. The distributor does not pay for the health officer's view.
- **Why this order of money:** distributors give daily usage and revenue now; the health signal is the mission and the long-term moat, but it needs a funded evaluation first.
- **Existing revenue line: Dischargely.** The founders' live product, a Gemini discharge-summary tool in a hospital that cuts a 30-40 minute summary to 10-15 minutes. It is already earning, and it produces doctor-confirmed medicine-to-diagnosis labels that can later improve the medicine-to-illness mapping. **It is not part of this build.**

## 8. Honest evidence statement (use this when asked)

Sales data has moved with illness in many studies, from no lead to a couple of weeks, best for respiratory products, weakest for diarrhoea medicines, and almost all from richer countries. In South Asia there is one small Bangladesh study. Sales are also moved by advisories and panic. So we do **not** claim early warning. We claim a testable hypothesis and we measure it live: ASHA ground truth gives us precision, and false alarms are counted and shown.
