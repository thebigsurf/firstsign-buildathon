# UX, accessibility and visual QA report (QA engineer 2)

Method: Playwright (Chromium) against http://localhost:8020. All 8 routes at 1440x900 and 390x844, light and dark; axe-core 4.10.2 on each; keyboard walk of inbox and ASHA record flow with a fake mic; API-blocked error states; 320px reflow with reduced motion. Screenshots are in docs/qa_screens/.

## Verdict
Looks like a real product: calm teal palette, strong hierarchy, simulated-data bar on every route, honest fallback labels, dark theme is good. axe found only 2 rule types. Main blemishes: horizontal scroll on Radar and Alert detail at phone width, the sticky Send bar covering the ASHA record button at 360x640, inconsistent alert counts, and a long tab path to Approve.

## Findings
| # | Sev | Finding |
|---|-----|---------|
| 1 | high | Horizontal scroll at 390px on /distributor/radar and /officer/alert/:id (scrollWidth 837 and 798). Cause: a `table.sr-only` (chart data table) with children 798px wide escapes the clip. On Radar at 1440 wide, scrollWidth also exceeds the viewport (desktop flagged). Also on Radar a nowrap link (`inline-flex min-h-11 whitespace-nowrap`, right edge 421) overflows 390. Breaks checklist 32/49. |
| 2 | high | ASHA record screen at 360x640: the fixed bottom Send bar overlaps the 120px record button (button is cut off until the user scrolls; Send is disabled and visually dominant). Primary action should be fully visible without scroll. |
| 3 | medium | Inconsistent counts: Stock radar header says "Alert areas: 6, Watch areas: 2" (per pin code) while the Officer page says "Open alerts 3" (merged alerts). Judge will ask which is right. Label radar as "pin codes" or align numbers. |
| 4 | medium | Inbox keyboard path: Approve is about 30 Tab stops away (10 message rows, then each line has Change, qty, Not available, Remove). Add a skip link or roving tabindex in the message list, and a shortcut to the action bar. Focus ring itself is good (3px outline on every stop). |
| 5 | medium | Inbox desktop has two h1 elements (page title plus the selected message title); phone has one. Checklist item 9 wants one h1. Radar: heading-order violation (h3 area card after h1, no h2). |
| 6 | medium | axe `region`: the simulated-data bar sits outside any landmark on every route (moderate). Wrap it in a `role="region"`/`aria-label` or put it inside the header. No contrast, name, label or ARIA violations anywhere in light or dark. |
| 7 | medium | Phone header on ASHA: "Change role" wraps to two lines and header actions are 44px, below the 56px rule (checklist 32). All in-flow buttons (visit, record 120px, type, send, not-you) are 56px+. |
| 8 | medium | ASHA flow depends on an officer having approved a visit list: with a fresh state ASHA sees "No visits yet" and a dead end. Demo script must approve the visit list first, or add a "Report without a visit list" path or seed one. |
| 9 | medium | Landing stat tiles show Orders read 0, Matched on first read 0%, ASHA reports 0, Alerts confirmed 0 on a fresh state. Four zeros weaken first impression; seed the demo state or hide until non-zero. |
| 10 | low | Inbox first message shows "Read in 39.3 s" in a model chip, plus an unexplained "marg" tag next to the pin/language line. Slow latency is visible honestly, but 39 s will be noticed live; warm the cache. Explain the tag or drop it. |
| 11 | low | Alert detail shows skeleton boxes for Drafted actions during the first 1-2 s and "data-only-fallback" with no sources when Gemini grounding failed. The fallback is honest ("no outside sources found... the web search step failed") but a judge sees Google Search grounding not working. Warm the explain cache before demo. |
| 12 | low | ASHA prompt for visit 1 is in Marathi while page chrome is Hindi/English; fine if the ASHA's language is Marathi, but make the language chip visible. |
| 13 | low | React Router v7 future-flag warnings in the console on every load (not errors; zero console errors on all routes). Set the future flags. |
| 14 | low | Mobile full-page screenshots show the bottom tab bar overlapping content; this is a full-page-capture artefact of a fixed bar, but confirm content has bottom padding equal to the bar height at phone width (in the 390 viewport the Radar and Inbox lists scroll under it). |

## Passed
- Simulated demo data bar on all routes at both sizes, not dismissible (item 6).
- Inbox: matched pill, line confidence bars, Change, Not available, Remove, "Approving as" and disabled/enabled action bar with a plain-English summary; 2-pane at 1024+.
- Radar: ranked cards, level badge with icon and word, sparkline with dashed baseline and end label, suggested SKUs with reasons, "Ignored: single-shop spikes (1)" decoy.
- Officer map: circles differ in size and stroke, legend matches, list on phone with List/Map toggle; alert detail has a timeline, KPI tiles, drafted actions tagged "Drafted by AI, not sent", explanation, causes with confidence, honest empty sources.
- ASHA: Hindi first with English second, 120px record button, keyboard start/stop works with fake mic ("Start recording", "Recording stopped, 3 seconds", aria-live present), type and upload fallbacks, step indicator.
- Error states are designed (red panel with Details and Try again) on inbox, radar and officer when the API is blocked; empty states have copy.
- 320px width: no horizontal scroll on /, inbox, officer. Dark mode consistent, contrast fine (axe clean).

## Not tested
Mic-denied state, Gemini-live ASHA result tiles and done screen (backend fell back), zoom 200%, screen reader speech, grayscale test (only visually: badges carry words and icons).

## Rubric estimate (UX/usability/accessibility 10%): 7.5/10 as is, 9 after fixing items 1 and 2. Checklist blockers (6, 11, 12, 17, 28, 32, 45): item 32 partially fails (header targets 44px and overflow); the others pass in the paths tested.
