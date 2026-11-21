# FirstSign: the 12 hardest judge questions

Honest answers. Say the limit first, then the mitigation.

**1. Does medicine sales data really lead illness? Show me the evidence.**
Mixed. A 2014 review of 27 studies, all in high-income countries, found sales usually correlate with illness and lead it by none to about two weeks, best for cold and flu, weakest for diarrhoea. One small Bangladesh study saw ORS sales rise about a week before diarrhoea admissions. No South Asian study has tested pin-code level. Our pilot is the test, with ASHA ground truth and false alarms counted.

**2. How do you avoid false alarms?**
Breadth, not volume: an alert needs many chemists rising together, so one shop's bulk buy is suppressed (we show it as "ignored"). Chronic medicines are checked as a control. A single ASHA report is damped, and confirming takes two. A human approves every action. Target: under 1 false alert per pin code per month, to be measured.

**3. How accurate is the parsing?**
Measured on 10 simulated samples, live Gemini, no cache: 55 of 56 lines found (98%), no invented lines, no wrong-and-green errors. The miss was a dropped line in a Marathi note. Caveat: ten samples we wrote, not real traffic. A pilot will give a real number.

**4. What if the AI is confidently wrong?**
Four rules stop a line from being green: a spelling far from the listed one, a name shared by several items, the model saying it interpreted the line, or generic-word-only overlap. The clerk sees a reason on every yellow line, and a warning if words were left unplaced. Every approval stores what the model said and what the clerk changed.

**5. Which Google services are actually live?**
Gemini API for audio, vision, structured output and the agent; Cloud Run, Secret Manager, Cloud Build and Artifact Registry for deployment. Firestore and BigQuery AI.FORECAST are written as optional paths and off by default; we have not tested them at scale. Search grounding runs live on a billed key and returns cited sources.

**6. Your Google Search grounding shows real news for a simulated spike. Isn't that fake corroboration?**
Grounding is a live Google Search for the area and dates, shown as context, not as proof. The agent is told to report only what sources say and to call causes hypotheses. The order history in the demo is simulated and labelled; in the pilot the dates and orders are real.

**7. Is the data real?**
No. Order history, chemists, ASHAs and notes are simulated and labelled in every screen. The signal engine is deterministic and tested on the seeded events. The real test is the pilot. We use no patient names; ASHA reports hold counts only.

**8. Why will distributors pay?**
It frees part of a clerk and cuts wrong-item dispatches. Our estimate is Rs 3,000-4,500 per month per desk against Rs 0.4-0.7 per parsed order. These are estimates; the pilot validates them. The alert layer is the grant-funded public-health side.

**9. Why not a Marg plugin or a WhatsApp chatbot?**
Voice notes and handwriting are the real input, and Marg does not read them. We sit in front of Marg and write back to it; that is the first integration. We do not replace the clerk. We give him a checked draft.

**10. What about privacy and consent?**
Chemists' orders hold chemist ID, pin code, items and time, with no patient data. Audio and images are processed in memory and not kept. The API key is in Secret Manager. Signal is shown at pin-code level. A real deployment needs distributor and chemist consent and data-sharing terms, which the pilot will set.

**11. Does it scale, and what does it cost?**
Stateless FastAPI on Cloud Run, cached by input hash, with a model fallback chain and cooldown on quota errors. Cost is dominated by Gemini calls per message. Today's limits are the free-tier quota, and about 6 s per parse on the fallback model. A billed key and the faster models cut that; we have not load-tested.

**12. Why you, and what is the unfair advantage?**
We run Dischargely, a live Gemini product in a hospital (summaries from 30-40 minutes down to 10-15), so we know clinical safety, audit and fallbacks. Dischargely can later supply doctor-confirmed medicine-to-diagnosis labels, which no pure order desk has. We also placed 3rd at an Andhra Pradesh health-surveillance hackathon.
