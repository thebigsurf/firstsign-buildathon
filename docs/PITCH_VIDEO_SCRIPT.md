# FirstSign: 2-minute pitch video

Format: screen capture of the live link plus voiceover. 1080p, light theme, captions on. Record the app at 1440 px for desk shots and a 390 px window for the phone shot. Use the Hindi voice note (msg_02) and the Kurla alert. Voiceover is about 260 words; read at a calm pace.

## Shot list

| Time | Shot | Voiceover |
|---|---|---|
| 0:00-0:12 | Inbox list, 10 messages with mic and photo icons; slow scroll. | "Meet Aman, a clerk at a medicine distributor. Before lunch he has dozens of voice notes and photos of handwritten lists. One wrong brand, and he gets the blame." |
| 0:12-0:28 | Black slide, big numbers: **3,254** and **485**. | "India sees illness late. In 2023, death certificates recorded 3,254 dengue deaths. Surveillance recorded 485. The first sign was in the pharmacy orders." |
| 0:28-0:40 | Title card: FirstSign, with the line "the AI order desk that sees illness first". | "FirstSign reads every voice note and handwritten list and turns them into ready-to-bill orders. Because every order passes through, it also sees what is rising, and where." |
| 0:40-1:08 | Parse msg_02: transcript appears, five green lines, one yellow line highlighted with its reason; click Approve. Zoom on the yellow reason text. | "Gemini hears Hindi and Marathi, reads handwriting, and matches the catalogue. Green means sure. Yellow means unsure, and it says why. Nothing is silently corrected, and every approval is logged." |
| 1:08-1:22 | Radar: Kurla card, stock suggestions; highlight "Ignored: single-shop spikes". | "The distributor gets a stock radar: what to stock, and why. One shop buying in bulk does not trigger it." |
| 1:22-1:42 | Officer map, three alerts; open Kurla, press Explain, scroll the summary and drafted visit list; click Approve. | "The health officer sees a ranked list. A Gemini agent explains the rise, labels the cause a hypothesis, and drafts the visits. A person approves every action." |
| 1:42-1:54 | Phone: ASHA records, structured card appears; cut to officer, status turns **confirmed**. | "The ASHA reports by voice, in her own language. Two reports confirm the alert, and each becomes labelled ground truth." |
| 1:54-2:00 | End card: Cloud Run and Gemini marks, live URL, "Simulated data. Pilot is the real test." | "Built on Gemini and Google Cloud, by the team behind Dischargely, live in a hospital today. Let's run the pilot." |

## Recording notes
- Run `DEMO_SCRIPT.md` setup first so the cache is warm and the state is reset. Record each shot separately and cut; do not wait on a slow call on camera.
- Keep the simulated-data bar visible in every app shot.
- Do not show grounded sources unless the explain screen really lists them.
- Do not show the `.env`, terminal with keys, or the Cloud console secrets.
- Add captions in English; the Hindi note should have its English meaning as a subtitle.
