# FirstSign: final deck content (10 slides)

*Rubric key: F Functional 30, T Tech 20, G Google AI 20, P Problem fit 15, U UX 10, I Innovation 5. Numbers marked **measured** come from `docs/archive/QA_REPORT_functional_v1.md` (21 Nov, live Gemini, no cache). Everything else is labelled est. or target. Screenshots: final files go in `docs/screens/` (not yet created); until then use the `docs/qa_screens/` file named on each slide. Export as PDF, under 5 MB.*

*If the organisers' PDF template is required, map as: slide 2-3 = Problem, 4 = Solution, 5 = Architecture, 6 = Google AI tools, 7 = Google AI models, then keep 8-10 as appendix.*

## 1. Title
**FirstSign: the AI order desk that sees illness first.**
Google DeepMind x Google Cloud Startup Buildathon India 2026, Mumbai. Team, contact, live link, QR.

## 2. Problem (P)
- **The clerk drowns:** 80-120 order lines a day from voice notes and photos of handwritten lists, and gets blamed for a wrong brand.
- **The owner is blind:** stock-outs and expiry, no view of what is rising.
- **The system sees late:** 2023 death certificates recorded **3,254 dengue deaths; programme surveillance recorded 485**. Different definitions, but the gap shows how much severe illness never reaches surveillance.
- Chemists see the first sign. Nobody reads it.

## 3. Solution (P, I)
Orders in, bills out, a health signal as a by-product.
1. Reads voice and handwriting into ready-to-bill orders.
2. Stock radar for the distributor.
3. Ranked ASHA visit list for the health officer.
4. ASHA voice report in her own language confirms or cancels the alert and becomes labelled ground truth.

Human approves every action. AI uncertainty is always visible. Every approval is logged.
`[SCREENSHOT: docs/screens/landing_desk_light.png, fallback docs/qa_screens/landing_desk_light.png]`

## 4. Live product (F, U)
Three panels: `inbox_desk_light.png` (green, yellow, red lines), `officer_desk_light.png` (map with 3 alerts), `asha_phone_light.png` (record screen at phone width).
Caption: "Simulated history and chemists, labelled in the app. Live Gemini parsing."
Also available: dark theme, Hindi/Marathi/English labels, keyboard path, 320 px reflow.

## 5. Architecture (T, G)
Diagram: WhatsApp-style input -> FastAPI on **Cloud Run (asia-south1)** -> Gemini (parse, agent) -> signal engine (local; BigQuery AI.FORECAST optional) -> React and Leaflet front end.
Live in the demo: **Gemini API (google-genai), Cloud Run, Secret Manager, Cloud Build, Artifact Registry**. Optional, off by default: **Firestore, BigQuery**.
Engineering, all real: JSON response schema on every call, model fallback chain with cooldown after quota errors, disk cache by input hash, offline mode, magic-byte media checks, audit log, 135 backend tests, frontend lint, tsc and 41 vitest tests.

## 6. How we use Gemini (G)
| Job | Capability | Detail |
|---|---|---|
| Hear orders | Audio understanding | Hindi, Marathi, Hinglish voice notes |
| Read lists | Vision | Handwritten photos |
| Match catalogue | Structured output + abstention | Returns a SKU or `unknown`; a Latin spelling is matched, never guessed |
| Structure ASHA reports | Audio + JSON schema | Counts only, no names |
| Explain a rise | Reasoning model + Google Search grounding + tool use | Hypothesis, causes, three drafted actions. Grounding needs a billed key (see slide 8) |
| Resilience | Fallback chain | Fast tier for parsing, reasoning tier for the agent |

Show the live counters from About: calls, models, fallbacks, cache hits.

## 7. Measured results (F, T)
Ten sample orders (4 voice, 3 photo, 3 text), live Gemini, no cache, `gemini-3.1-flash-lite`, **measured before the final fixes**:

| Metric | Result |
|---|---|
| Lines found | 55 of 56 expected (98.2% recall) |
| Invented or wrong lines | 0 (100% precision) |
| Wrong-and-green errors | **0** |
| Parse latency | 3.6-8.5 s, median about 6 s |
| ASHA voice report to structured card | 4.5-5.9 s; 35 of 36 fields correct (4 samples, Hindi x3, Marathi x1) |
| Agent explanation | 6-8 s |
| Back-test on seeded history | Both seeded events alert, decoy chemist suppressed, quiet pin codes silent |

After the fixes (re-tested live): a correct Hindi order shows 5 green lines; "pan 20 patta" and "crosin 30" now show yellow with a reason; bad uploads return 400 with no quota spent; one ASHA report moves an alert by at most +1.0 log-odds, and **two** reports are needed to confirm. Live check on 21 Nov: two ASHA voice reports took the Kurla alert from 0.59 to 0.92, confirmed.
Honest note: the one miss was a dropped line in a Marathi note; a "check nothing is missing" warning now shows when the model lists words it could not place.

## 8. Evidence, honestly (P)
- Bangladesh, one Dhaka-area community, one season: ORS sales rose about a week before diarrhoea admissions (unadjusted), about 2 days before after adjusting for temperature.
- 2014 review of 27 studies, all high-income countries: sales usually correlate with illness, lead none to about two weeks; strongest for cold and flu, weakest for diarrhoea.
- **No South Asian study has tested this at pin-code level. Our pilot is the test**, with false alarms counted and ASHA ground truth.
- Design answers: breadth across chemists (a bulk-buy decoy does not alert), damped single reports, human approval, precision reported.
- Platform honesty: the demo key is free-tier, so Google Search grounding shows "not run" rather than a faked source. Deployed with a billed key it returns cited sources.

## 9. Business model (est., to be validated)
- **Distributors pay monthly:** Rs 3,000-4,500 per desk, because it frees part of a clerk. Cost per parsed order Rs 0.4-0.7.
- **Public-health side is grant-funded:** district pilots, Rs 25 lakh-2 Cr.
- **Dischargely**, our live Gemini product in a hospital, is the existing revenue line and a source of doctor-confirmed labels (not in this build).

## 10. Why us, pilot, asks
**Why us:** Dischargely (live in a hospital, discharge summary 30-40 min down to 10-15), 3rd place at an Andhra Pradesh health-surveillance hackathon, product and engineering that ships.
**90-day pilot:** 5 distributors in Mumbai (Kurla, Sion, Chunabhatti belt), 1 ward health officer, 10 ASHAs; Marg write-back; back-test on known outbreaks with a pre-registered rule.
**Targets (est.):** order entry time -40%, alert precision >= 50%, under 1 false alert per pin code per month.
**Asks:** introductions to a Mumbai distributor association and a ward health office; Google Cloud credits and Gemini quota; public-health evaluation mentors.
