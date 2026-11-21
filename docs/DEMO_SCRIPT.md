# FirstSign: demo script (final)

*Rubric key: F Functional 30, T Tech 20, G Google AI 20, P Problem fit 15, U UX 10, I Innovation 5. The back end of every step below was run against the live app on 21 Nov (parse, radar, alerts, explain, two ASHA reports confirming an alert).*

## Setup (5 minutes before)
1. `cd backend; python -m app.warm` fills the cache so repeats are instant. Start the app (`bash run_local.sh`, or the Cloud Run URL).
2. Check `/api/health` shows `status: ok`. Reset state: `curl -X POST <url>/api/demo/reset`.
3. Laptop for distributor and officer, phone (or a 390 px window) for ASHA. Keep a second tab on the officer page.
4. If the network or quota fails, restart with `DEMO_OFFLINE=1`. The flow is identical and results are labelled `offline-sample`. Never claim a live call you did not make.

## A. Live demo, 3:00

| Time | Click path | Say | Rubric |
|---|---|---|---|
| 0:00-0:15 | `/` landing: three roles, the simulated-data bar. | "A distributor's clerk gets hundreds of voice notes and photos of handwritten lists. FirstSign turns them into bills, and as a side effect sees illness before the hospital does." | P |
| 0:15-1:05 | `/distributor/inbox`, open the **Hindi voice note (msg_02)**, Parse. Five green lines. Point at the unnamed children's syrup (yellow, with a suggested item and a reason). Choose the right item, press Approve. | "Gemini hears Hindi and matches the catalogue in one step. Green is sure, yellow is unsure, red is unknown, and it always says why. Nothing is silently corrected." | F, G, U |
| 1:05-1:20 | Open a handwritten photo (msg_05), Parse. Then open the audit view (`/api/audit`). | "Same screen for handwriting. Every approval logs what the model said and what the clerk changed. The clerk is protected." | F, T |
| 1:20-1:45 | `/distributor/radar`. Open the Kurla diarrhoea card: stock suggestions and reason. Point at "Ignored: single-shop spikes (1)". | "Stock up on these, and here is why. One chemist bulk-buying is high volume, low breadth, so it does not alert." | P, F |
| 1:45-2:20 | `/officer`: map with three alerts (Matunga and Sion, Kurla, Govandi and Mankhurd). Open **Kurla**, press Explain. Read the summary, the cause marked as a hypothesis, the drafted visit list. Edit one line, approve the visit list. | "A Gemini agent reads our counts, explains the rise and drafts three actions. It labels the cause a hypothesis. A person approves every action." | G, F, P |
| 2:20-2:55 | Phone `/asha`. Pick Sunita (400070). Choose a locality, record or upload a Hindi note: "Chawl mein 18 ghar dekhe, 6 mein dast aur ulti, paani ganda aa raha hai." Show the structured card. Repeat once as Shabana (also 400070) on another locality, with a different count (for example 17 homes, 5 cases). Two different ASHAs and at least 25 homes between them are needed. Back on officer: Kurla now **confirmed**. | "She speaks in her own language. Gemini structures counts, no names. Two reports from two different ASHAs confirm the alert, and each becomes labelled ground truth." | G, U, I |
| 2:55-3:00 | `/about`: Gemini counters, simulated-data note. | "Everything is measured live. The history is simulated and labelled. The pilot is the real test." | T, P |

Only click what is listed. Do not mention Firestore or BigQuery as live, and do not claim cited web sources unless the explain screen shows them.

## Known limits, say if asked
- On the free-tier key, Google Search grounding returns no sources and the screen says so. With a billed key it is live.
- Run `python -m app.warm` before going on stage. msg_03 (Marathi) is then cached; cold, it falls back to a labelled sample after 25 s. Approving an order changes the alert counts, so a cached explanation is replaced by the last saved Gemini explanation (labelled) if Gemini is down.
- Confirming an alert takes two reports above normal from two different ASHAs, 25 homes or more between them, on purpose. One report, or two from the same ASHA, moves confidence but leaves it open. The two bundled sample recordings (14 and 15 homes) are enough, uploaded as two different ASHAs.
- The faster models (3.5-flash, 3.8-flash, 4-hydrogen) are quota-limited on the free key; the chain falls back to 3.1-flash-lite (about 6 s per parse).

## If something fails
Open a message that is already parsed (instant), keep talking, switch to the second officer tab. Never apologise on stage.

## Judge one-liners
- *Does sales data really lead illness?* "Mixed evidence: none to two weeks, best for respiratory. One small Bangladesh study saw ORS sales lead diarrhoea admissions by about a week. Nobody has tested pin-code level in South Asia. Our pilot is that test, and ASHA reports give us precision."
- *What stops false alarms?* "Breadth across chemists, damped ASHA reports, two to confirm, a human approval gate."
- *Why Gemini?* "Audio, vision, structured output, grounding and tool use in one family, with regional-language voice."
