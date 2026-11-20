# FirstSign: Design Specification (v1, 20 Nov 2026)

Owner: Head of Product Design. Audience: the frontend developer (implements exactly this), the UX QA engineer (scores against section 9). Stack: Vite + React + TypeScript + Tailwind. Routes and API shapes come from `ARCHITECTURE.md` sections 5 and 6; this file never changes them.

All contrast ratios quoted below were computed with the WCAG 2.x relative-luminance formula, not estimated.

---

## 1. Mood and identity

### Visual idea (one line)
**"A clinical chart that listens": calm chart-paper surfaces, one steady pulse line, and signals that are always words first and colour second.**

### Who is looking, and what that demands

| User | Device and context | Design consequence |
|---|---|---|
| **Order clerk**, 24, at a Dava Bazaar stockist | Desktop, 1366x768 or 1920x1080, a pile of WhatsApp messages, many orders an hour, scared of billing a wrong strength | Dense but quiet two-pane workspace. Keyboard-first. Uncertainty is loud, everything else is calm. Never auto-corrects. |
| **District health officer** | Laptop, 1280-1536px, thinks in maps and ranked lists, must justify a visit to a superior | Map plus ranked list, evidence one click deep, every claim shows its source and confidence. Looks like an official instrument, not a toy. |
| **ASHA worker** | Cheap Android, 360x640, direct sunlight, one hand, mostly Hindi or Marathi, low data literacy | One task per screen, 48px+ targets (we use 56px), high contrast, huge record button, labels in her language first. |

### Tone
Trustworthy, calm, Indian, clinical-grade but warm. Think a well-run pathology report crossed with a good railway timetable: precise, legible, no decoration that does not carry meaning. Warmth comes from language ("Is this right?", "Dhanyavaad") and rounded-but-not-bubbly shapes, not from decoration.

### What it is NOT
- No purple or blue-to-purple gradients, no glassmorphism, no glowing orbs, no sparkle icons for "AI".
- No cream plus terracotta. No beige editorial look.
- No emoji as icons, anywhere. Icons are a single outline SVG set (Lucide, 1.75px stroke, 20px default, 24px in ASHA view).
- No stock illustrations of smiling doctors. The only illustration is the pulse line motif and the map.

### Brand motif: the pulse line
A thin horizontal line with one small spike (an ECG blip), drawn in `--accent`. It is used in exactly three places: the logo mark, the section divider on the landing page, and the recorder idle state. It is the only decorative element in the product. Spec: SVG path `M0 12 H18 L22 4 L27 20 L31 12 H64`, stroke 2px, round caps, `fill: none`.

### Logo
Wordmark "FirstSign" in the display face, weight 700, with the pulse-line mark (24px) left of it. "First" in `--text`, "Sign" in `--accent`. Hindi tagline under it on the landing page: "पहला संकेत" (pehla sanket, "the first sign"), lang="hi".

### Voice and copy rules
- Plain English, short sentences, no jargon: say "Check this line", not "Low-confidence entity resolution".
- Say what the AI is unsure of, and why, in one sentence.
- Never say "AI-powered", "magic", "seamless". Say what happened: "Read from voice note, 2.1 s".
- Hindi labels appear next to English for role names, primary actions, and the entire ASHA flow (Hindi first, English second there). Marathi (`mr`) shown when the ASHA's language is `mr`.

---

## 2. Design tokens

### 2.1 Colour (CSS variables, light and dark)

Theme is set by `data-theme="light|dark"` on `<html>`, defaulting to `prefers-color-scheme`. A header toggle (sun/moon icon button, aria-label "Switch theme") persists to `localStorage` in a try/catch.

```css
:root,
:root[data-theme="light"] {
  /* Surfaces */
  --bg:            #F4F7F8;  /* page: faint cool chart paper */
  --surface:       #FFFFFF;  /* cards, panels */
  --sunken:        #E9EEF0;  /* table headers, inset wells, input rest */
  --text:          #0F1F26;  /* ink */
  --muted:         #4A5D66;  /* secondary text */
  --border:        #C5D1D6;  /* decorative dividers (not for control edges) */
  --border-strong: #6F8791;  /* control edges: inputs, checkboxes (3:1 vs surface) */

  /* Brand accent: deep clinical teal-blue */
  --accent:        #0B5C7A;
  --accent-fg:     #FFFFFF;  /* text on accent */
  --accent-soft:   #DCEFF5;
  --accent-text:   #0B5C7A;  /* accent used as text/link/icon on bg or surface */

  /* Signal levels (area level) */
  --normal:        #1F7A4D;  --normal-bg: #DDF2E6;
  --watch:         #8A5A00;  --watch-bg:  #FFF0CC;
  --alert:         #B3261E;  --alert-bg:  #FDE3E1;

  /* Confidence (line and alert confidence) */
  --conf-high:     #1F7A4D;  --conf-high-bg: #DDF2E6;
  --conf-unc:      #8A5A00;  --conf-unc-bg:  #FFF0CC;
  --conf-unk:      #B3261E;  --conf-unk-bg:  #FDE3E1;

  /* Map fills (circle fill; stroke uses the text colour variable above) */
  --map-normal: #2E9E66;  --map-watch: #E0A21A;  --map-alert: #D64538;

  /* Focus */
  --focus-ring: #0B5C7A;
  --focus-halo: #FFFFFF;

  /* Elevation */
  --shadow-1: 0 1px 2px rgb(15 31 38 / 0.08), 0 1px 1px rgb(15 31 38 / 0.04);
  --shadow-2: 0 4px 12px rgb(15 31 38 / 0.10), 0 1px 3px rgb(15 31 38 / 0.06);
  --shadow-3: 0 12px 32px rgb(15 31 38 / 0.18);
  --scrim:    rgb(15 31 38 / 0.55);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* same block as data-theme="dark" below */ }
}
:root[data-theme="dark"] {
  --bg:            #0C1519;
  --surface:       #142127;
  --sunken:        #0F1A1F;
  --text:          #E8F0F2;
  --muted:         #9DB1B9;
  --border:        #2E434C;
  --border-strong: #5F7B86;

  --accent:        #5CC0E0;
  --accent-fg:     #06222D;
  --accent-soft:   #12323D;
  --accent-text:   #7CCDE8;

  --normal:        #5FD18F;  --normal-bg: #123524;
  --watch:         #F2B84B;  --watch-bg:  #3A2A07;
  --alert:         #FF8A80;  --alert-bg:  #40161A;

  --conf-high:     #5FD18F;  --conf-high-bg: #123524;
  --conf-unc:      #F2B84B;  --conf-unc-bg:  #3A2A07;
  --conf-unk:      #FF8A80;  --conf-unk-bg:  #40161A;

  --map-normal: #3DBB7E;  --map-watch: #F2B84B;  --map-alert: #FF6B5E;

  --focus-ring: #7CCDE8;
  --focus-halo: #0C1519;

  --shadow-1: 0 1px 2px rgb(0 0 0 / 0.5);
  --shadow-2: 0 4px 12px rgb(0 0 0 / 0.5);
  --shadow-3: 0 12px 32px rgb(0 0 0 / 0.65);
  --scrim:    rgb(0 0 0 / 0.65);
}
```

The developer must duplicate the dark block under the `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` guard so first paint matches the OS without JavaScript.

Tailwind mapping (`tailwind.config.ts`): `theme.extend.colors` points every token to its variable using the `rgb(var(--x) / <alpha-value>)` form, or plain `var(--x)` where alpha is not needed. Required names: `bg, surface, sunken, text, muted, border, borderStrong, accent, accentFg, accentSoft, accentText, normal, normalBg, watch, watchBg, alert, alertBg, confHigh, confHighBg, confUnc, confUncBg, confUnk, confUnkBg`. Always use these names; never raw hex in components.

### 2.2 Signals are never colour alone
Every level and confidence has a fixed **word + icon + colour** triple. Colour-blind safe by construction.

| State | Word (EN / HI) | Icon (Lucide) | Shape on map |
|---|---|---|---|
| normal | Normal / सामान्य | `check-circle-2` | solid thin ring, smallest |
| watch | Watch / निगरानी | `eye` | dashed ring, medium |
| alert | Alert / चेतावनी | `triangle-alert` | solid thick ring plus fill, largest |
| matched (high) | Matched / मिलान | `check` | n/a |
| uncertain | Check this / जाँचें | `help-circle` | n/a |
| unknown | Not found / नहीं मिला | `octagon-x` | n/a |

### 2.3 Typography

Google Fonts (load with `display=swap`, preconnect both hosts):

```
https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Noto+Sans:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap
```

| Role | Family | Weights | Use |
|---|---|---|---|
| Display | Bricolage Grotesque | 600, 700 | Page titles, hero, card titles, numbers in KPIs |
| Body | Noto Sans | 400, 500, 600 | All UI text |
| Devanagari | Noto Sans Devanagari | 400, 500, 600, 700 | Any Hindi/Marathi; also fallback for Display so headings never fall to a system font |
| Mono | JetBrains Mono | 500, 600 | Quantities, SKU IDs, ratios, pin codes, timers |

Why this pairing: Bricolage gives headings a confident, slightly humanist-grotesque character that is distinctly not "AI startup default"; Noto Sans plus Noto Sans Devanagari share proportions, so mixed English and Hindi lines sit on one baseline rhythm. Mono for numbers makes columns align and quantities unmistakable.

```css
:root {
  --font-display: "Bricolage Grotesque", "Noto Sans Devanagari", system-ui, sans-serif;
  --font-body:    "Noto Sans", "Noto Sans Devanagari", system-ui, sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, Consolas, monospace;
}
body { font-family: var(--font-body); font-feature-settings: "tnum" 1; }
:lang(hi), :lang(mr) { line-height: 1.6; } /* Devanagari needs more leading */
```

Type scale (rem at 16px root; line-height in brackets). Devanagari text gets +0.1 line-height automatically via `:lang`.

| Token | Size | Weight / family | Use |
|---|---|---|---|
| `text-display` | 3rem (1.1) | 700 display | Landing hero (desktop). 2.25rem on mobile. |
| `text-h1` | 2rem (1.2) | 700 display | Page titles |
| `text-h2` | 1.5rem (1.25) | 600 display | Section titles |
| `text-h3` | 1.125rem (1.35) | 600 display | Card titles |
| `text-body` | 1rem (1.5) | 400 body | Default |
| `text-sm` | 0.875rem (1.45) | 400/500 body | Table cells, meta. Minimum for desktop. |
| `text-xs` | 0.75rem (1.4) | 600 body, uppercase tracking 0.04em | Badges and column heads only. Never for sentences. |
| `text-num` | 1rem | 500 mono | Qty, ratio |
| `text-num-lg` | 2.25rem (1) | 600 mono | KPI numbers, timer |
| `text-asha` | 1.25rem (1.5) | 500 body | ASHA body text (larger base) |
| `text-asha-h` | 1.75rem (1.3) | 700 display | ASHA headings |

Rule: no text below 12px anywhere; no sentence below 14px; ASHA view never below 18px.

### 2.4 Spacing, radius, elevation, focus

- **Spacing:** Tailwind default 4px scale. Page gutters: 16px (mobile), 24px (tablet), 32px (desktop). Card padding: `p-4` mobile, `p-5` desktop. Gap between cards: `gap-4`. Section vertical rhythm: `space-y-6`.
- **Touch targets:** `min-h-11` (44px) for all interactive elements in desktop views on touch devices; ASHA view `min-h-14` (56px), above the 48px floor.
- **Radius:** `--r-sm: 6px` (badges, inputs), `--r-md: 10px` (buttons, cards), `--r-lg: 16px` (modals, big panels), `--r-full` (pills, record button). Tailwind: `rounded-md` set to 6, `rounded-lg` to 10, `rounded-xl` to 16.
- **Elevation:** three levels only. Cards `shadow-1` plus 1px `--border`; popovers and dropdowns `shadow-2`; modals `shadow-3`. In dark mode rely on border and surface step rather than shadow.
- **Focus ring (global):**
```css
:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
  box-shadow: 0 0 0 5px var(--focus-halo);
  border-radius: inherit;
}
```
Ring is 7.43:1 on white and 9.21:1 on dark surface. Never `outline: none` without this replacement.

---

## 3. Layout system and navigation

### 3.1 App shell
```
+--------------------------------------------------------------------+
| [pulse] FirstSign     [Distributor | Health officer | ASHA]  [theme] |  header 56px, sticky
+--------------------------------------------------------------------+
| SIMULATED DEMO DATA: orders and history are simulated. About       |  notice bar 32px, sticky, never dismissible
+--------------------------------------------------------------------+
|  (sub-nav for the active role: tabs)                                |
|  page content                                                       |
+--------------------------------------------------------------------+
```

- **Header:** logo link to `/`; **role switcher** is a segmented control (`role="tablist"` semantics are wrong here, use a `<nav aria-label="Choose your role">` with three links, the current one `aria-current="page"`). Labels: "Distributor / वितरक", "Health officer / स्वास्थ्य अधिकारी", "ASHA / आशा". Links go to `/distributor/inbox`, `/officer`, `/asha`. Right side: theme toggle, "About" link (`/about`).
- **Notice bar:** background `--watch-bg`, text `--watch`, icon `flask-conical`, text: "Simulated demo data. Chemist orders and 90-day history are simulated, no real patients or people." (Hindi on wider screens: "यह डेमो डेटा है, असली नहीं।"). Always visible, in the shell, on every route including `/`. On the ASHA mobile view it collapses to a 28px single line: "Simulated demo data / डेमो डेटा".
- **Sub-nav:** Distributor: tabs "Inbox / इनबॉक्स", "Stock radar / स्टॉक रडार", "Audit log / ऑडिट". Officer: "Map and alerts" (and "Audit log"). ASHA: none (single flow). Tabs are links with `aria-current`, 44px tall, bottom border 3px `--accent` on current.
- **Audit log** is a shared view reachable from the Distributor sub-nav and Officer sub-nav. It has no route in the contract, so it is rendered at `/distributor/inbox?view=audit` and `/officer?view=audit`, as a right-hand drawer on desktop and a full-screen sheet on mobile. (Logged in `CONTRACT_REQUESTS.md` as "no new route needed".)

### 3.2 Breakpoints and responsive rules

| Name | Min width | Behaviour |
|---|---|---|
| base | 0 | Single column, bottom-sheet modals, ASHA design target is 360px |
| `sm` | 640 | 2-column KPI grids |
| `md` | 768 | Sub-nav inline; inbox becomes two panes only from `lg` |
| `lg` | 1024 | Two-pane inbox (320px list + flexible detail); officer map splits |
| `xl` | 1280 | Officer: map 60% / panel 40%; max content width 1440 |

Max content width `max-w-[1440px]` centred. Never horizontal page scroll; wide tables scroll inside their card with `overflow-x-auto` and a sticky first column.

### 3.3 ASHA mobile-first rules
- Canvas is 360x640 first. Single column, `px-4`.
- Everything interactive is `min-h-14 min-w-14`; spacing between targets at least 12px.
- Body text `text-asha` (20px); contrast of body text 15.7:1; large buttons use accent background with white text (7.43:1).
- No hover-dependent UI. No tiny icon-only buttons: icons always carry a visible label.
- Bottom action bar is fixed (`fixed inset-x-0 bottom-0`, `pb-[env(safe-area-inset-bottom)]`), height 88px, holding the one primary action. Content has `pb-28`.
- Language: UI strings Hindi first with English beneath at `text-sm text-muted`. Locale chosen from the ASHA's `language` field; Marathi strings supplied where listed below, otherwise Hindi.
- The ASHA view defaults to the light theme on first visit (bright ambient light), with a clearly labelled theme toggle; a saved choice is respected afterwards.

---

## 4. Screen-by-screen specs

Common to all screens: data comes from the API in section 5 of the contract. Every fetch has a loading, empty, error state. Standard patterns:
- **Loading:** skeleton blocks (`bg-sunken`, 1.2s opacity pulse 0.6 to 1.0, disabled under reduced motion) shaped like the final content. Spinners only inside buttons. Never a blank panel.
- **Error:** inline panel with `triangle-alert` icon, one plain sentence ("We could not reach the server."), a "Try again" button, and the technical message in a collapsed "Details" disclosure. `role="alert"`.
- **Empty:** icon, one-sentence explanation, one action. Never a bare "No data".

### 4.1 `/` Landing

**Purpose:** in 10 seconds a judge understands the product, and picks a door.

**Layout (desktop):**
1. **Hero** (two columns, 7/5): left has H1, subhead, the pulse-line divider; right has a static "preview card" showing one real parsed order line pair (yellow uncertain line and green matched line) so the product is visible without clicking.
   - H1: "Know which medicine is moving before the clinic fills up."
   - Subhead: "FirstSign turns the WhatsApp orders chemists already send into ready-to-bill orders, and spots early signs of illness in the same stream."
   - Hindi tagline under logo: "पहला संकेत".
2. **Three role doors** (grid `md:grid-cols-3 gap-4`), each a card that is one big link (whole card clickable, one tab stop, `aria-label` equals title plus "open"):
   - **Distributor / वितरक**, icon `package-check`, "Turn voice notes and photo lists into bills. See what to stock." Button "Open inbox" to `/distributor/inbox`.
   - **Health officer / स्वास्थ्य अधिकारी**, icon `map-pinned`, "See where illness is rising and send ASHAs first." Button "Open map" to `/officer`.
   - **ASHA / आशा**, icon `mic`, "Record what you saw in your own language." Button "Start visit" to `/asha`.
   Card recipe: surface, border, `rounded-xl p-6`, icon in a 48px `accent-soft` circle, title `text-h3`, body `text-body text-muted`, bottom-aligned button. Hover: border becomes `--accent`, shadow-2; no movement.
3. **How it works** (3 steps in a row; vertical on mobile), numbered with mono numerals in accent circles, joined by the pulse line:
   1. "Chemists send orders as they always do." (voice note or photo of a handwritten list)
   2. "FirstSign reads them. A clerk checks and approves." (every uncertain line shown, nothing silently changed)
   3. "Rising groups trigger a visit list. ASHAs confirm on the ground." (and every report teaches the system)
4. **Trust strip:** four small facts with icons: "Every approval is logged", "Nothing is corrected silently", "No patient names stored", "Simulated demo data".
5. **Footer:** link to `/about`; "Built for the Google DeepMind x Google Cloud Startup Buildathon India 2026".

**States:** static page except the preview card, which is static markup (no fetch). The live KPI strip beneath hero (optional) pulls `/api/metrics`: shows 4 numbers (orders parsed, auto-matched %, ASHA reports, alerts confirmed); if it fails, the strip is hidden without an error banner.

**Mobile:** hero stacks; preview card below subhead; doors stack; each door min-h 96px.

### 4.2 `/distributor/inbox` Inbox and parsed order

**Purpose:** the clerk turns each WhatsApp message into a correct bill-ready order, fast, and can see exactly what the AI is unsure of.

**Layout (`lg+`):** two panes, full viewport height minus shell (`h-[calc(100dvh-var(--shell-h))]`), each pane scrolls independently.
- **Left pane, 340px: message list** (WhatsApp-like, but in our palette).
- **Right pane: parsed order workspace.**
Below `lg`: the list is the page; selecting a message navigates to a full-screen detail with a back button ("Back to messages"); state kept in `?msg=<id>`.

**Left pane components**
- Header: "Messages" `text-h3`, count badge, filter chips: "All / New / Parsed / Approved" (single-select `role="radiogroup"`).
- Message row (72px, `button`, selected row `bg-accent-soft` plus 3px left accent bar):
  - Avatar: 40px circle with shop initials (`bg-sunken`), not a photo.
  - Line 1: shop name (`font-semibold`) and time (right, `text-sm text-muted`, mono).
  - Line 2: type icon (`mic`, `image`, `message-square-text`) + preview: voice shows "Voice note 0:23", photo shows "Photo of handwritten list", text shows first 40 chars truncated. Pin code and language chip (hi/mr/en) at far right.
  - Status pill at row end: New (accent outline), Parsed (watch if any uncertain/unknown lines, else normal), Approved (normal filled with check). Pill uses word plus icon.
- Selecting a row calls `POST /api/orders/parse` if status is `new` (the clerk can also press "Read this message" first; auto-read on select is on, so judging does not need extra clicks). Results cached in memory per message id.

**Right pane regions (top to bottom)**
1. **Message header:** shop name, owner first name, pin and area, language, received time, software tag ("Paper" / "Marg"). Right: model name chip `gemini-3.5-flash` and latency "Read in 2.1 s" (mono, `text-sm`, muted). This proves the Google AI use to a judge without being shouty.
2. **Source panel** (collapsible, open by default; 2 columns on `xl`):
   - Voice: audio player (native `<audio controls>` styled lightly) and the **transcript** with language label (e.g. "Hindi transcript"), transcript text in `lang` of the message. Transcript words that belong to uncertain lines are underlined with a 2px dotted `--conf-unc` underline and hover/focus linked to the line.
   - Photo: image with zoom (click toggles 1x/2x, `cursor-zoom-in`, Escape closes); each parsed line shows a small "Show on photo" button that draws a 2px `--accent` rectangle if the API returns coordinates; if not available the button is not rendered.
   - Text: the raw message in a monospace-free quote block.
3. **Summary strip** (4 chips): "6 lines", "4 matched" (green), "1 check this" (yellow), "1 not found" (red). Chips are anchors that scroll to and focus the first line of that status. A big sentence under it, plain: "Check 2 lines before you approve."
4. **Order table** (the core). Columns (desktop):

| Column | Content | Notes |
|---|---|---|
| Status | icon plus word badge | matched/uncertain/unknown, 112px |
| What they said | `raw_text` in the original script, `lang` set | italic not used; shown in a quote-tinted cell `bg-sunken` |
| Matched product | brand + strength + form + pack, e.g. "Pan-D 40 mg tablet, strip of 15"; molecule in `text-sm text-muted`; group chip | click to open the alternatives dropdown |
| Qty | mono number, editable (`input type="number" inputmode="numeric" min=0`) | with unit label after (strip/box) |
| Confidence | 52px bar plus mono percent, "92%" | bar fill uses confidence colour, never alone |
| Actions | "Change" (dropdown), "Not available" toggle, "Remove" | icon+label at `lg`, icon+tooltip+aria-label below |

   - **Row backgrounds:** matched: `surface`; uncertain: `conf-unc-bg` with a 4px left border `--conf-unc`; unknown: `conf-unk-bg` with a 4px left border `--conf-unk`. Row also shows the status word, so colour is never alone.
   - **Why is this uncertain?** Under the matched product in uncertain rows, a one-line reason (`text-sm`): "Heard 'pan di' – could be Pan-D 40 or Pantop-D 40." Derived from the API `alternatives` (top two scores); the frontend composes the sentence from data, it does not invent reasons.
   - **Alternatives dropdown** (`role="listbox"` popover, up to 5 items from `alternatives`, plus "Search catalogue..." typeahead against `/api/catalogue` using client-side fuzzy match, plus "Mark not available"): each option shows brand, strength, pack, and score as a percent. Keyboard: Arrow keys, Enter selects, Escape closes, Home/End. After a choice, the row shows an **"Edited" tag** and the original AI guess in small struck-through text ("AI read: Pan-D 40") so the edit is never silent. Status becomes "matched (clerk confirmed)", with a user icon.
   - **Unknown rows:** the product cell shows "No match in your catalogue" and a primary-outline "Pick product" button that opens the same typeahead. Qty still editable if one was heard.
   - **Qty edit:** inline. On change, show the previous value under the field ("was 10") until approval. Qty 0 is invalid (inline error "Enter 1 or more").
   - **Not available items:** a separate section "Not available / नहीं है" listing `not_available` strings from the API plus lines the clerk toggled. Each is a chip with an x. They go on the order as a note, not as billed lines. Copy: "These were asked for but are not in your stock list."
   - **Add line** button at table foot ("Add a line"), opens the typeahead.
5. **Notes:** `notes` from API in a muted block "Note from the AI: ..." (read-only).
6. **Sticky approval bar** (bottom of the right pane):
   - Left: running totals "6 lines, 2 changed by you, 1 not available".
   - Middle: "Approving as" select (the clerk's name; demo names: "Clerk: Rohan", "Clerk: Sneha"; simulated) so `approved_by` is explicit.
   - Right: **"Approve and send to billing"** (primary). **Disabled until every uncertain and unknown line is resolved** (confirmed, changed, marked not available, or removed). While disabled, a visible sentence says why: "2 lines still need a check." Clicking the disabled button is not possible; the sentence is an `aria-describedby` target.
   - Secondary: "Re-read message" (re-parse), "Skip".
7. **After approval:** `POST /api/orders` fires; the message becomes Approved; a success toast "Order saved. Logged as approved by Rohan." with "View in audit log" action. The row in the list updates and selection advances to the next New message (focus moves to the first line in the new detail). The table becomes read-only with an "Approved by Rohan at 11:42" banner (`normal-bg`) and a "View audit" link.

**States**
- List loading: 6 skeleton rows. Empty: "No messages yet. New orders from chemists appear here." Error: standard.
- Detail loading while parsing: a 3-step progress strip inside the pane, "Listening / Reading / Matching to your catalogue" with elapsed seconds (mono). Skeleton table rows underneath. If parsing takes more than 8 s, add "Still working. The AI can take a few seconds on voice notes."
- Parse error: panel "We could not read this message." Buttons "Try again", "Enter manually" (opens an empty table with Add line). Offline mode (`/api/health.offline === true`): a discreet chip "Demo mode: results are pre-recorded" beside the model chip. Never hide this.
- Empty parse (no lines): "No medicines found in this message." with Enter manually.

**Interactions summary:** `J/K` or Arrow Down/Up in the list changes message; `Enter` in list focuses first line needing a check; `Tab` order: filter chips, list, source panel, summary chips, table rows (row-by-row: status, product button, qty, actions), notes, approval bar. There is deliberately no single-key approve shortcut, to prevent accidental billing. Approve requires a click or Enter on the focused button.

### 4.3 `/distributor/radar` Stock radar

**Purpose:** "Stock up on these, here is why." Calm, ranked, evidence-backed.

**Layout:** page title "Stock radar / स्टॉक रडार"; a one-line explainer "Medicine groups rising in your area compared with normal. Simulated history for demo." Top row KPI chips: "Alert areas: 2", "Watch areas: 3", "Data as of 19 Nov 2026" (from `as_of`). Filter chips by group (from `/api/groups`, with `label_hi`), multiselect. Then a **card grid** (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4`), ranked by urgency: level (alert before watch), then ratio descending.

**Area card (`RadarCard`)**
- Header: rank number (mono, muted), area name `text-h3`, pin (mono chip), level badge (right).
- Group row: group label and Hindi label, group chip with the group's `color_hint` as a 10px dot only (never as the sole carrier of meaning).
- Big number: ratio "2.5x normal" (`text-num-lg`), subtext "15 chemists ordering above normal" (from `chemists_affected`, plain sentence).
- **Sparkline** (full card width, 56px high): last 30 days of `series.units` as a 2px line in the level colour; the baseline as a dashed `--muted` line; area between line and baseline lightly filled (alpha 0.12) when above. Last point is a 6px dot with a label of today's value. Axes hidden, but there is a visually-hidden table alternative (`<table class="sr-only">`) and `role="img"` with `aria-label="Fever orders in Kurla over the last 30 days: today 38 units, normal 15."`. Legend inline under it: "- - normal range" and "-- orders".
- **Suggested stock** list (from `skus`): rows with brand, strength, a mono "+240 strips" (suggested_qty with unit), and the `reason` text under it (`text-sm text-muted`). Show top 3, "Show all 6" expands. Each row has a checkbox "Add to my reorder list".
- Footer: "Why is this rising?" link to `/officer/alert/:id` when an alert exists for that pin and group (distributors may read; read-only view note appears there), and a "Copy reorder list" button producing plain text (toast "Reorder list copied").
- **Decoy handling:** when a single chemist drives a spike (breadth low) the API gives level normal; the card, if shown at all, uses level Normal and the note "One shop ordering in bulk (scheme). Not a wider rise." Shown in a separate collapsed section "Ignored: single-shop spikes" so the clerk sees the system declined to alert. This demonstrates judgment to judges.

**States:** loading = 6 card skeletons; empty = "Nothing is rising right now. We check every time an order is approved."; error standard. Sort control: "Urgency (default) / Biggest rise / Area name".

### 4.4 `/officer` Map and alerts

**Purpose:** the officer sees where, ranks where to send ASHAs, and opens an alert.

**Layout (`xl`):** map left (60%), alert panel right (40%), both full height below the shell. Below `lg`: map on top (45dvh), alert list below; a "List / Map" toggle on mobile switches between them, default List.

**Map**
- Leaflet, OpenStreetMap tiles with the required attribution visible (`© OpenStreetMap contributors`). In dark theme apply a CSS filter on tile pane only: `filter: brightness(0.75) contrast(1.1) saturate(0.7)` (no inverted tiles).
- Initial view fits all pin centroids (Mumbai, `fitBounds` with 32px padding).
- **Circles at pin centroids** (`/api/pincodes`), joined with `/api/signal` for level of the highest-ratio group in that pin:
  - radius in metres: normal 350, watch 600, alert 900. Fill opacity: normal 0.12, watch 0.25, alert 0.35. Stroke weight: normal 1, watch 2 dashed (`dashArray: "6 4"`), alert 3 solid. Colours from `--map-*`.
  - Pin code label (mono 11px, via `L.divIcon`, white halo) at alert and watch centroids only.
  - Hover/focus tooltip: "Kurla 400070: Diarrhoea 2.5x normal, Alert".
  - Click selects the area: the right panel scrolls to and highlights the matching alert card.
- **Legend** (bottom-left control, `bg-surface` card with border): three entries, each showing the actual circle style (solid thin / dashed / solid thick) plus the word, plus "Circle size = how far above normal". Below, a small line "Simulated history for demo".
- **Group selector** (top-right overlay, a select): "All groups" default, or one group; changes which group colours circles.
- **Keyboard / screen reader:** Leaflet markers are not reliably accessible, so the alert list is the accessible equivalent. The map container has `role="application" aria-label="Map of illness signals by pin code. The same information is in the alert list next to it."` and `tabindex="0"`; arrow keys pan (Leaflet default), `+`/`-` zoom. Each circle layer is also reachable: provide a visually hidden list of buttons inside the map region ("Kurla 400070, alert") that call the same select function.

**Alert panel (right)**
- Header: "Alerts / चेतावनियाँ" and counts; segmented filter "Open / Confirmed / Dismissed / All" (default Open).
- **Alert card** (ranked by level then confidence):
  - Title: group label + area list ("Diarrhoea: Kurla, Sion, Chunabhatti"), pins as mono chips.
  - Level badge; ratio "2.5x"; breadth "9 of 12 chemists above normal" (plain sentence from `breadth`).
  - **Confidence meter:** a 120px horizontal bar, percentage mono, word (High, Moderate, Low) with the colour triple. Under it, "ASHA reports: 2" and a status chip (Open / Confirmed / Dismissed).
  - Started: "Rising since 14 Nov (6 days)".
  - Button "Open alert" to `/officer/alert/:id`; the whole card is also clickable; select in the map on hover/focus (no navigation until click).
- **"Where to send ASHAs next" ranked list** (card above alerts on `xl`, tab on smaller): numbered localities from the latest approved visit list, if none yet: "No visit list yet. Open an alert and approve one." This is the Froncort-style output, so it is prominent: title "Visit next / अगला दौरा".
- A **KPI row** above the map panel: Open alerts, Confirmed by ASHAs, Chemists covered, As-of date.

**States:** map tiles fail: a banner over the map "Map tiles did not load. The list still works." (circles hidden; list intact). No alerts: "No alerts. All areas look normal today." with a green check. Loading: grey map placeholder plus 3 skeleton cards.

### 4.5 `/officer/alert/:id` Alert detail

**Purpose:** explain why, show evidence and sources, draft actions, human approves.

**Layout (`lg+`):** two columns, left 7/12: story; right 5/12: actions. Mobile: single column, actions below with sticky "Review actions" jump link.

**Header:** back link "All alerts", H1 "Diarrhoea rising in Kurla, Sion, Chunabhatti", level badge, status chip, confidence meter, "Rising since 14 Nov". Beneath, three evidence stats in a row (mono large numbers): ratio "2.5x", breadth "9 of 12 shops", z-score as "far above usual" (the raw z in mono, small, as tooltip text).

**Left column**
1. **Signal chart:** larger sparkline version (200px) per affected pin, small multiples (max 3 visible, "Show all" for the rest), each with baseline dashed. Title: "Orders vs normal, last 30 days". `role="img"` plus sr-only table.
2. **"Why we think this" – the agent's explanation.**
   - Label above: "Explained by Gemini with Google Search" with the model name chip and latency (this is the Google AI integration showpiece; keep it factual, not decorated). Subtle `accent-soft` panel, border-left 4px `--accent`.
   - `summary` in `text-body` (2-4 sentences).
   - **Likely causes** (ordered list): each shows the cause title `font-semibold`, evidence sentence, confidence badge (High/Moderate/Low with colour triple and percent). Max width of text 65ch.
   - **Our own signal checks**, a short "What our data shows" list the frontend assembles from the alert fields (not from the agent): "Many shops: 9 of 12", "Several neighbouring pins moving together", "Respiratory orders flat, so not a general bad-air week". Each has a check icon. If a check fails, `circle-x` and muted text, honest.
   - **Sources:** list `sources` as external links (`rel="noopener noreferrer" target="_blank"`), each with the domain in muted mono and an `external-link` icon, link text is the page title. Heading "Sources found with Google Search". If empty: "No outside sources found. The explanation uses our order data only." Never hide an empty state.
   - Generation states: **loading** shows a staged strip ("Checking order data", "Searching for outbreak reports", "Writing the explanation"), 5-15 s expected; **error** with retry; cached results show chip "Saved from earlier. Regenerate" (calls explain again).
3. **ASHA reports** feed: each report as a compact card: ASHA first name, locality, time, "12 households, 5 with diarrhoea, 3 children", water issue badge; empty: "No reports yet." This is where ground truth appears. New reports animate in (see section 8).

**Right column: drafted actions** (the approvals card stack). Three action cards (`distributor_note`, `officer_note`, `asha_visit_list`) in a vertical stack. Each:
- Title with icon: "Note to distributor / वितरक को सूचना", "Note for the district office", "ASHA visit list / आशा दौरा सूची".
- A **"Drafted by AI, not sent"** tag (watch-bg) until approved; after approval it becomes **"Approved by Dr. Meera at 11:42"** (normal-bg, check icon). Wording is fixed so the state is unmistakable.
- Body is an editable `textarea` (min 5 rows, auto-grow) pre-filled with the draft; for the visit list, a **sortable list** of `{name, landmark, priority, reason}` rows, each with priority chip (High/Medium/Low), drag handle optional but a keyboard alternative is required: "Move up" / "Move down" icon buttons with aria-labels, and a "Remove" button. Rows show reason text. Locality names have `lang` if Hindi.
- If the text differs from the draft: show "Edited by you" tag and keep a "Reset to draft" link. The `edited_text` is what is sent to `/api/actions/approve`.
- Footer: "Approving as" select (demo officers, labelled simulated) and **"Approve action"** primary button. After approval: success toast, the card locks (text read-only) with an "Undo" not offered (audit integrity); instead "View in audit log".
- Approving `asha_visit_list` makes it show up in `/asha` for the matching ASHAs. Add the line "ASHAs in these pins will see this list on their phones." under the button.
- A note under the whole stack: "Nothing is sent until you approve it. Every approval is logged."

**Other states:** alert not found: "We could not find this alert." with link back. Dismissed alert: banner and read-only.

### 4.6 `/asha` ASHA flow (mobile-first)

**Purpose:** a worker with one hand and bad light records what she saw, confirms the structured result, and sees that her report mattered.

A single screen with four steps (state machine: `list` -> `record` -> `confirm` -> `done`), each step fills the viewport; progress is shown as 4 dots with text "Step 2 of 4 / चरण 2 / 4" at top (the dots are `aria-hidden`; text is the accessible progress).

**Step 0: Who am I (first load only).** A select of ASHAs from `asha.csv`-backed list (first names only, simulated): "Choose your name / अपना नाम चुनें" with large radio cards (56px). Remembered in `localStorage` in try/catch. Her language sets UI language.

**Step 1: Visit list "आज के दौरे" (Today's visits)**
- Heading `text-asha-h`: "आज के दौरे / Today's visits". Subline: name and pin.
- Fetched from `GET /api/asha/visits?asha_id=`. Cards, one per locality, ranked: rank number in a 40px circle, locality name (`text-asha-h` small), landmark (`text-asha`), `priority` chip, and the `reason` in plain Hindi/English where provided. Each card has a full-width button "रिपोर्ट करें / Record report" (56px).
- **Empty:** "अभी कोई दौरा नहीं। जब अधिकारी सूची मंज़ूर करेंगे, वह यहाँ दिखेगी।" / "No visits yet. When the officer approves a list it will appear here." plus a "Refresh / ताज़ा करें" button.
- **Error / offline:** "इंटरनेट नहीं है / No internet" with Retry.

**Step 2: Record "बोलकर बताइए" (Speak)**
- Locality chip at top (name, landmark).
- **Prompt card** with 3 gentle cues (not a form): "कितने घर देखे? बुखार, दस्त, खाँसी वाले कितने? बच्चे कितने? पानी की कोई दिक्कत?" / "How many homes? How many with fever, loose motions, cough? Children? Any water problem?" These help a fresh user, but speaking freely is fine.
- **Record button:** a 120px circle (`rounded-full`), accent background, `mic` icon 48px, label under it "दबाकर बोलना शुरू करें / Tap to start". Tap to start, tap to stop (not press-and-hold; hold is tiring and fails with a sweaty thumb). Recording state: button turns `--alert` background with a square stop icon, label "रोकने के लिए दबाएँ / Tap to stop", pulsing ring (disabled under reduced motion; in that case a solid ring and the timer carry the state).
- **Live waveform and timer:** canvas 100% wide, 72px high, drawn from an `AnalyserNode` (bars, 3px wide, 2px gap, bar colour `--accent`, background `--sunken`). Timer in `text-num-lg` mono "00:12". A text label "रिकॉर्डिंग चल रही है / Recording" sits next to a solid red dot (the dot is also text-labelled). Max 90 s with a visible countdown at 80 s. A `role="timer"` element is not announced every second; announce at start, at 30/60/80 s, and at stop via an `aria-live="polite"` region.
- **Permission denied:** panel with plain instructions "माइक्रोफ़ोन की अनुमति चाहिए। ब्राउज़र की सेटिंग में 'अनुमति दें' चुनें।" with image-free steps, and the fallback below.
- **Fallbacks (always visible below the button, text links styled as 56px outline buttons):** "फ़ाइल चुनें / Upload an audio file" and "लिखकर बताएँ / Type instead" (textarea; sends as `text`).
- After stop: playback bar (play, replay), buttons "दोबारा रिकॉर्ड करें / Record again" (secondary) and "भेजें / Send" (primary, in the sticky bottom bar).
- Sending: full-width staged progress "सुन रहे हैं... / Listening", elapsed seconds; failure: "Try again" and keeps the recording in memory.

**Step 3: Confirm "क्या यह सही है?" (Is this right?)**
- Result card from `POST /api/asha/report`: a 2-column grid of big stat tiles (each 56px+, number in `text-num-lg`, label below in Hindi then English): घर देखे / Homes visited, बुखार / Fever, दस्त / Diarrhoea, खाँसी / Cough, साँस की दिक्कत / Breathing, चकत्ते / Rash, बच्चे प्रभावित / Children affected, रेफर किए / Referred, plus a full-width row "पानी की समस्या / Water issue" with a Yes/No toggle (switch with text "हाँ / Yes", "नहीं / No").
- Each tile is tappable to correct (opens a bottom-sheet numeric stepper with `-` and `+` buttons 56px and the number between). Corrected tiles show "बदला गया / Edited". Nothing is silently changed.
- **Transcript** shown under the tiles as "आपने कहा / What you said" in her language (`lang`), collapsed after 3 lines with "और दिखाएँ / Show more".
- Low confidence handling: if a number came from an ambiguous phrase, the API's `notes` is shown in a yellow box "यह जाँच लें / Please check" (the frontend shows `notes` verbatim, never invents).
- Sticky bottom bar: primary "हाँ, सही है / Yes, correct" (this confirms; the record is already saved by the API, so the confirm step stamps "confirmed" in the UI and it is also logged to audit by calling the contract's report endpoint only once; the confirm button therefore does not post again). Secondary: "बदलें / Change".

   Contract note: the API structures and saves on `POST /api/asha/report`. If the product needs a separate confirm, request `POST /api/asha/report/confirm` in `CONTRACT_REQUESTS.md`; until then the frontend treats "Yes, correct" as the UI acknowledgement, and edits made by the ASHA are carried in a follow-up report submission with `text` containing the corrected figures. (Simplest compatible option.)

**Step 4: Done "धन्यवाद!" (Thank you)**
- Large check icon in a 96px `normal-bg` circle. Heading: "आपकी रिपोर्ट मिल गई / Report received".
- **Alert confidence change card** (the payoff): "इस इलाके की चेतावनी / Alert for this area". Shows the previous confidence and new confidence as two bars with numbers, e.g. "62% -> 81%", word "पक्की हुई / Confirmed" or "कमज़ोर हुई / Weakened" if confidence dropped, with one plain sentence: "आपके 5 दस्त के मामलों से चेतावनी और पक्की हुई।" / "Your 5 diarrhoea cases made the alert stronger." If no alert found: "कोई चेतावनी नहीं बदली / No alert changed."
- Buttons: "अगला दौरा / Next visit" (primary), "सूची पर वापस / Back to list".

**Language strings** are in a `strings.ts` with `hi`, `mr`, `en` keys; if `mr` is missing a key the Hindi string is used. Marathi supplied for: record prompt "किती घरे पाहिली? ताप, जुलाब, खोकला किती?", "रेकॉर्डिंग सुरू करा", "रिपोर्ट मिळाली".

### 4.7 `/about` How it works
- Purpose: a judge reads this to see rigor. Single column, `max-w-3xl`.
- Sections: (1) "What FirstSign does" in 3 short paragraphs; (2) **How it works** diagram, an inline SVG flow: WhatsApp message -> Gemini reads (voice, photo) -> Catalogue match -> Clerk approves -> Counts per pin code -> Signal (baseline, breadth, co-movement) -> Agent explains with Google Search -> Officer approves -> ASHA visits -> Voice report structured by Gemini -> Confidence updates (loop back). Boxes use tokens; arrows are 1.5px `--muted`; colour is not needed to understand it. (3) **Design for blame**: four bullets (AI shows what it is unsure of, nothing silently corrected, every approval logged with a name and time, a human approves every outbound action). (4) **Data rules** (copied from the contract section 3). (5) **Simulated data notice** in a `watch-bg` panel stating what is simulated. (6) **Google technology used**: a table of Gemini models by job (parsing, agent, grounding), Cloud Run, optional Firestore/BigQuery, each with one line on why. Facts must match the live `/api/health` response, which the page fetches to show the models actually in use.

### 4.8 Audit log view (drawer/sheet, section 3.1)
- Title "Audit log / ऑडिट लॉग". Intro: "Every approval and every edit, with who and when."
- Table from `GET /api/audit`, newest first: time (mono, IST), who (`approved_by`), what (order, action type), detail (for orders: "3 lines edited, 1 marked not available"; expandable to a per-line diff: "Pan-D 40 -> Pantop-D 40, qty 10 -> 12"), object link (to message or alert).
- Filters: type (Orders / Actions / ASHA reports), search by name. Export CSV button (client-side) "Download log".
- Empty: "Nothing logged yet. Approvals appear here as they happen." Error: standard. Immutable look: no edit/delete controls anywhere.

---

## 5. Component inventory (Tailwind recipes)

Tailwind classes reference the token names from section 2.1. `cx()` merges classes. All interactive components inherit the global focus ring.

### 5.1 Buttons
```
base:      inline-flex items-center justify-center gap-2 font-semibold rounded-lg
           min-h-11 px-4 text-sm transition-colors duration-150
           disabled:opacity-60 disabled:cursor-not-allowed
primary:   bg-accent text-accentFg hover:brightness-110 active:brightness-95
secondary: bg-surface text-text border border-borderStrong hover:bg-sunken
ghost:     text-accentText hover:bg-accentSoft
danger:    bg-alert text-surface hover:brightness-110   /* use sparingly: "Reject", "Dismiss alert" */
sizes:     sm  = min-h-9 px-3 text-sm
           md  = min-h-11 px-4 text-sm   (default)
           lg  = min-h-12 px-5 text-base
           asha= min-h-14 px-6 text-xl w-full rounded-xl
icon-only: min-h-11 min-w-11 p-0 + aria-label required
loading:   replace label with spinner (16px, 2px stroke), keep width, aria-busy="true"
```
Primary in dark: `bg-accent text-accentFg` = 7.9:1. `danger` text in dark mode uses `text-bg` (dark text on light salmon) because `--alert` is light there: contrast `#0C1519` on `#FF8A80` is above 8:1. Implement as `bg-alert text-bg dark:text-bg` and in light `text-surface`; define `--on-alert` as `#FFFFFF` (light) and `#0C1519` (dark) if preferred. Disabled primary on approval bar must still have a visible reason sentence.

### 5.2 Badges and pills
```
badge base:  inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold uppercase tracking-wide
level normal: bg-normalBg text-normal      + icon check-circle-2
level watch:  bg-watchBg  text-watch       + icon eye
level alert:  bg-alertBg  text-alert       + icon triangle-alert
conf high:    bg-confHighBg text-confHigh  + icon check
conf unc:     bg-confUncBg  text-confUnc   + icon help-circle   (label "Check this")
conf unk:     bg-confUnkBg  text-confUnk   + icon octagon-x     (label "Not found")
status new:   border border-accent text-accentText
status approved: bg-normalBg text-normal + icon badge-check
edited tag:   bg-sunken text-text border border-borderStrong + icon pencil, label "Edited"
group chip:   bg-sunken text-text rounded-full px-2.5 py-0.5 text-sm + 10px dot (aria-hidden)
```
Icon size 14px, always `aria-hidden="true"`, the word is the accessible name. Pill version (for filters): `rounded-full` with `min-h-9 px-3`.

### 5.3 Cards
```
card:       bg-surface border border-border rounded-lg shadow-1 p-4 md:p-5
card-link:  card + hover:border-accent hover:shadow-2 transition-shadow
panel-info: bg-accentSoft border-l-4 border-accent rounded-md p-4        (agent explanation)
panel-warn: bg-watchBg text-watch border border-watch rounded-md p-3
panel-error:bg-alertBg text-alert border border-alert rounded-md p-4 (role="alert")
panel-ok:   bg-normalBg text-normal border border-normal rounded-md p-3
```
Text inside `panel-*` uses the paired token for contrast (verified in section 7); body text inside still `text-text` where longer than one line.

### 5.4 Inputs
```
input:   w-full min-h-11 rounded-md border border-borderStrong bg-surface px-3 text-body
         placeholder:text-muted focus-visible:ring (global) aria-invalid:border-alert
label:   block text-sm font-medium mb-1
help:    text-sm text-muted
error:   text-sm text-alert flex gap-1 + icon (error text is linked via aria-describedby)
qty:     input + font-mono text-right w-24
```
Labels always visible (no placeholder-only labels).

### 5.5 Tables
```
table wrapper: card overflow-x-auto p-0
th: bg-sunken text-xs uppercase tracking-wide text-muted text-left px-3 py-2 sticky top-0
td: px-3 py-3 text-sm border-t border-border align-top
row-hover: hover:bg-sunken/60
order row uncertain: bg-confUncBg border-l-4 border-l-confUnc
order row unknown:   bg-confUnkBg border-l-4 border-l-confUnk
```
Below `lg`, order rows become stacked cards (each line a card with the same left border), never a squeezed table.

### 5.6 Map legend
```
legend: absolute bottom-3 left-3 z-[1000] bg-surface border border-border rounded-lg shadow-2 p-3 text-sm
item:   flex items-center gap-2; swatch is a 20px SVG circle drawn exactly like the map (stroke style, fill opacity)
title:  text-xs uppercase tracking-wide text-muted ("Level")
footer: text-xs text-muted ("Circle size = how far above normal. Simulated history for demo.")
```

### 5.7 Sparkline
Pure inline SVG, no chart library (keeps bundle small and styling exact).
```
viewBox 0 0 200 56, preserveAspectRatio="none", w-full h-14
line:      stroke-[2] fill-none, stroke var(--level colour), stroke-linejoin round
baseline:  stroke-[1.5] stroke-dasharray="4 3" stroke var(--muted)
fill:      path closed to baseline, fill var(--level colour) opacity-0.12
end dot:   r=3.5 on last point + text label (units) right-aligned above it
```
Must expose `role="img"` with generated aria-label and an sr-only `<table>` of the last 14 days.

### 5.8 Confidence meter
```
track: h-2 w-28 rounded-full bg-sunken ; fill: h-2 rounded-full, width = confidence*100%,
       colour: >=0.75 conf-high, 0.45..0.74 conf-unc, <0.45 conf-unk
label: mono percent + word (High / Moderate / Low) beside the bar
```
Role `meter` with `aria-valuenow/min/max` and `aria-valuetext="81 percent, high"`.

### 5.9 Recorder
Anatomy in 4.6. Recipes:
```
record button idle:  h-[120px] w-[120px] rounded-full bg-accent text-accentFg shadow-2
                     flex items-center justify-center  + focus ring offset 4
record button live:  bg-alert text-surface (light) / text-bg (dark) + ring-4 ring-alert/30 pulse
waveform:            h-[72px] w-full rounded-xl bg-sunken (canvas, devicePixelRatio aware)
timer:               font-mono text-num-lg tabular-nums
```
`aria-label` toggles: "Start recording" / "Stop recording"; `aria-pressed` reflects state. Live region announces transitions.

### 5.10 Toast
```
container: fixed bottom-4 right-4 (desktop) | inset-x-4 bottom-24 (ASHA, above the action bar) z-50 space-y-2
toast:     bg-surface text-text border border-border rounded-lg shadow-2 p-3 pr-10 flex gap-3 max-w-sm
           left bar 4px by type: success normal, error alert, info accent
role:      success/info "status" (aria-live polite); error "alert" (assertive)
timing:    success 5s, info 5s, error stays until dismissed; pause on hover/focus; dismiss button 44px
```

### 5.11 Modal and bottom sheet
```
scrim: fixed inset-0 bg-scrim ; dialog: bg-surface rounded-xl shadow-3 max-w-lg w-[calc(100%-2rem)] p-6
mobile: becomes bottom sheet: fixed inset-x-0 bottom-0 rounded-t-xl, max-h-[85dvh] overflow-auto
a11y:   role="dialog" aria-modal="true" aria-labelledby, focus trap, Escape closes, focus returns to trigger,
        background gets inert
```
Use for: confirm dismiss alert, qty stepper (ASHA sheet), catalogue search on mobile.

### 5.12 Empty state
```
wrapper: flex flex-col items-center text-center gap-3 py-12 px-6
icon:    48px in 64px bg-sunken rounded-full, text-muted
title:   text-h3 ; body: text-body text-muted max-w-sm ; action: one button (optional)
```

### 5.13 Skeleton
`bg-sunken rounded-md animate-[pulse_1.2s_ease-in-out_infinite]` and `motion-reduce:animate-none`.

### 5.14 Notice bar
`sticky top-14 z-40 bg-watchBg text-watch text-sm px-4 py-1.5 flex items-center gap-2 border-b border-watch/40` (contrast 5.25:1 light, 7.75:1 dark).

### 5.15 Segmented control / role switcher
Container `inline-flex rounded-lg bg-sunken p-1`; item `min-h-9 px-3 rounded-md text-sm font-medium text-muted hover:text-text`; current `bg-surface text-text shadow-1 aria-[current=page]` with 2px `--accent` underline for non-colour cue. On mobile: icon plus short label (Dist. / Officer / ASHA) shown in a bottom tab bar (64px) instead of the header.

### 5.16 Icon set
Lucide (tree-shaken imports). Sizes: 14 (badge), 16 (inline), 20 (default), 24 (ASHA), 48 (empty, record). No filled emoji, no unicode pictograms.

---

## 6. Accessibility checklist (WCAG 2.2 AA)

### 6.1 Contrast of every token pair (computed)

| Pair | Light | Dark | Needs |
|---|---|---|---|
| `text` on `bg` | 15.68 | 15.99 | 4.5 |
| `text` on `surface` | 16.88 | 14.24 | 4.5 |
| `text` on `sunken` | 14.43 | 15.30 | 4.5 |
| `muted` on `bg` | 6.40 | 8.29 | 4.5 |
| `muted` on `surface` | 6.89 | 7.38 | 4.5 |
| `muted` on `sunken` | 5.89 | 7.93 | 4.5 |
| `accent-text` on `surface` | 7.43 | 9.21 | 4.5 |
| `accent-text` on `bg` | 6.90 | 10.34 | 4.5 |
| `accent-text` on `accent-soft` | 6.27 | 7.59 | 4.5 |
| `accent-fg` on `accent` (primary button) | 7.43 | 7.90 | 4.5 |
| `normal` on `normal-bg` (also conf-high) | 4.54 | 7.05 | 4.5 |
| `watch` on `watch-bg` (also conf-unc, notice bar) | 5.25 | 7.75 | 4.5 |
| `alert` on `alert-bg` (also conf-unk) | 5.37 | 6.83 | 4.5 |
| `normal` on `surface` | 5.32 | 8.62 | 4.5 |
| `watch` on `surface` | 5.93 | 9.19 | 4.5 |
| `alert` on `surface` | 6.54 | 7.21 | 4.5 |
| `alert` on `bg` | 6.07 | 8.09 | 4.5 |
| `border-strong` on `surface` (control edges) | 3.78 | 3.65 | 3.0 (non-text) |
| `border-strong` on `bg` | 3.51 | 4.10 | 3.0 |
| `focus-ring` on `surface` | 7.43 | 9.21 | 3.0 |

`--border` (decorative dividers) is 1.56:1 and is allowed only because it is never the sole indicator of a control or state. Developer must not use `--border` on input edges or checkboxes. `normal` on `normal-bg` in light is 4.54, which passes with almost no margin: do not lighten either value and do not use these as text below 14px semi-bold (they are only used in 12px+ bold badges where the word is large enough in effect; keep the font-weight 600). Map fills (`--map-*`) are non-text graphics and are always accompanied by stroke style, labels and the list, so they need no text contrast.

Run the checks in CI or a script at the end (`docs/` may include the small Python snippet used here; any WCAG checker is fine).

### 6.2 Keyboard
- Skip link as first tab stop: "Skip to main content", visible on focus.
- Landmarks: `header`, `nav aria-label`, `main id="main"`, one `h1` per route.
- Inbox: list is a `role="listbox"`-free simple list of buttons; roving tabindex is not used (Tab moves through rows is acceptable but long); instead arrow keys move between rows (`aria-keyshortcuts`), `Enter` opens. Table inputs are reachable in DOM order. Alternatives dropdown follows the ARIA combobox/listbox pattern. No keyboard traps; modals trap focus and restore it.
- Map: see 4.4; the alert list is the keyboard path to all information.
- Visit list reorder: Move up / Move down buttons, `aria-live` announces "Moved to position 2 of 5".
- Recorder: Space or Enter toggles; no press-and-hold.
- All shortcuts documented in a "Keyboard help" popover (`?` key); no single-letter shortcut triggers a destructive or approving action.

### 6.3 Screen reader
- Recorder: button `aria-label` toggles; `aria-pressed`; a polite live region announces "Recording started", "30 seconds", "Recording stopped, 24 seconds"; waveform canvas is `aria-hidden`.
- Level and confidence badges read as words ("Alert", "Check this").
- Order table uses real `<table>`, `<th scope>`; changed cells have visually hidden text "edited by you, was 10".
- Sparkline `role="img"` with generated label plus sr-only table.
- Toast regions `aria-live`; errors `role="alert"`.
- Status of approval is exposed as text, not only a colour or icon.
- `aria-busy` on regions while loading; skeletons are `aria-hidden`.

### 6.4 Language
- `<html lang="en">`; every Hindi run wrapped with `lang="hi"`, Marathi `lang="mr"` (including `raw_text` and transcripts from the API, which carry their own language code).
- Do not mix scripts inside one `aria-label`; provide the English label and let the visible Hindi sit in its own element with `lang`.
- Devanagari minimum size 16px (14px for Latin) because of conjunct legibility.

### 6.5 Motion and other
- `@media (prefers-reduced-motion: reduce)`: disable all animations and transitions except opacity cross-fades under 100ms; replace pulse with a static ring; the waveform draws bars but without smoothing animation.
- Respect `prefers-contrast: more`: raise `--border` to equal `--border-strong`, and thicken focus ring to 4px.
- Forms: errors are text, associated, and not colour-only; do not clear user input on error.
- Zoom: layout works at 200% zoom and at 320 CSS px wide (reflow). No text in images.
- Target size: minimum 24x24 CSS px (WCAG 2.2) everywhere, with our own floor at 44px (desktop touch) and 56px (ASHA).
- No timeouts that lose work; the 90s record cap is announced and the audio is kept.
- Media: provide the transcript with every audio element.

---

## 7. Dark theme notes
- Dark is a first-class theme, not an inversion: surfaces step from `bg` (#0C1519) to `surface` (#142127); borders do the work shadows cannot.
- Signal colours lighten rather than saturate; fills on the map are brighter than light-mode fills so circles keep presence over dimmed tiles.
- Images (photos of handwritten lists) are never filtered. A subtle `border border-border` frames them.

---

## 8. Micro-interactions

### 8.1 Worth one moment of delight (max 4, each under 700ms)
1. **ASHA report confirms an alert:** when the alert's confidence changes, in the ASHA "Done" step the new confidence bar animates from the old value to the new (600ms, ease-out) and the number ticks up. On the officer map and alert detail (if open, via polling every 20 s or on focus), the alert's circle does **one** subtle pulse: radius scales 1.0 -> 1.08 -> 1.0 and stroke opacity 1 -> 0.6 -> 1 over 700ms, once, then rests. Plus a new report card slides in from above (200ms) in the ASHA reports feed, with a `status` announcement "New report from Sunita: alert confidence now 81%".
2. **Order approved:** the approved row group collapses its yellow/red tints to neutral over 250ms, and a check icon draws itself (stroke-dashoffset, 300ms) in the banner. Then the next message is selected.
3. **Uncertain line resolved:** its row background cross-fades from yellow to surface (200ms) and the left border thins; the summary chip counter ticks down. This makes the clerk feel progress toward the enabled Approve button.
4. **Agent explanation arrives:** text fades in line-group by line-group in 3 steps (not typewriter, which feels slow and fake), 120ms each. Sources then appear.

### 8.2 What NOT to animate
- No page-transition animations, no parallax, no confetti, no bouncing, no animated gradients, no looping idle animation anywhere except the recorder pulse while recording (and the skeleton).
- Never animate data values on the radar or the inbox (numbers must be steady and trustworthy); only the confidence meter after an ASHA report.
- Never animate color alone as a cue; never auto-scroll a table the user is editing; no auto-dismiss of errors.
- No sound. No vibration except one short haptic (`navigator.vibrate(30)`, ignored if unsupported) on record start and stop in the ASHA view.

---

## 9. Visual QA checklist (UX QA engineer: score each 0 / 1 / 2, total /108)

Score 2 = fully meets, 1 = partially, 0 = fails. Screenshot light and dark at 1440x900, 1024x768, and 360x640 (ASHA).

**Identity and tone (10)**
1. No purple gradients, no cream/terracotta, no emoji icons anywhere.
2. Pulse-line motif appears only in logo, landing divider, recorder idle.
3. Palette matches tokens (spot check 5 elements with devtools).
4. Display font on headings, mono on all quantities, ratios, pins, timers.
5. Tone: plain English, Hindi present where specified.

**Shell and navigation (8)**
6. "Simulated demo data" bar visible on every route, not dismissible.
7. Role switcher present, current role marked, works by keyboard.
8. Theme toggle works; no flash of wrong theme on reload.
9. Skip link works; one h1 per route.

**Inbox (20)**
10. Two panes at 1024+, list left, order right.
11. Uncertain rows are yellow with the word "Check this" and a reason sentence.
12. Unknown rows are red with "Not found" and a "Pick product" action.
13. Each line shows raw text, matched SKU, qty, confidence.
14. Alternatives dropdown works by keyboard and mouse.
15. Edited lines show "Edited" and the original AI guess; nothing silent.
16. "Not available" items are listed separately.
17. Approve is disabled with a visible reason until all flagged lines are resolved.
18. Approval records the approver and shows the audit link.
19. Model name and latency visible; offline demo mode chip visible when offline.

**Radar (8)**
20. Cards ranked by urgency; level badge has word and icon.
21. Sparkline shows baseline dashed and a labelled end value.
22. Suggested SKUs with quantities and one-line reasons.
23. The decoy (single-shop bulk order) is shown as "not a wider rise".

**Officer map and alert detail (16)**
24. Circles differ by size, stroke style and colour (colour-blind check in grayscale).
25. Legend matches the real circle styles.
26. Click on circle selects the alert; list and map stay in sync.
27. Alert detail shows explanation, causes with confidence, sources as real links, empty-source state honest.
28. "Drafted by AI, not sent" tag until approval; "Approved by X at time" after.
29. Draft text is editable; edited drafts flagged; visit list reorderable by keyboard.
30. A pulse on the circle after an ASHA report; once only.
31. Map tile failure falls back to the list.

**ASHA (16)**
32. All targets 56px or larger at 360px; no horizontal scroll.
33. Hindi first with English second; body text at least 20px.
34. Record button 120px, tap-to-start tap-to-stop, with visible timer and waveform.
35. Mic denied state gives plain steps and the upload/type fallbacks.
36. Result tiles editable; edited tiles flagged.
37. Done screen shows previous vs new confidence in words and bars.
38. Works in light theme under simulated bright glare (contrast check at 15.7:1 body text).
39. Bottom action bar clears the browser bar and safe area.

**Audit, About, Landing (8)**
40. Audit lists who, what, when and per-line edits.
41. About page models match `/api/health`.
42. Landing: three doors, 3-step "how it works", visible without scrolling more than one screen on desktop.
43. All routes show loading, empty and error states (trigger each by throttling or stopping the API).

**Accessibility (10)**
44. Tab through every route with no traps and visible 3px focus ring.
45. Contrast: no text below 4.5:1 (run an automated check, e.g. axe).
46. Screen reader announces recorder state, toasts, level and confidence words.
47. Hindi runs carry `lang`.
48. Reduced motion respected (toggle OS setting, confirm no animation).
49. Zoom 200% and 320px width reflow without loss.
50. No information carried by colour alone (grayscale screenshot test).

**Polish (4)**
51. Spacing follows the 4px scale; consistent card padding.
52. No layout shift when fonts load (`font-display: swap` plus size-adjust fallback).
53. No console errors on any route.
54. Empty, loading and error states are designed, not default browser text.

Pass bar: 90/108 raw (about 83%). Anything scoring 0 in items 6, 11, 12, 17, 28, 32, 45 is a blocker (these are the "design for blame", safety and accessibility promises).

---

## 10. Implementation notes for the frontend developer
1. Create `src/styles/tokens.css` with section 2.1 verbatim, import in `main.tsx`; configure Tailwind to use the variables.
2. Build the primitives in section 5 first (`Button`, `Badge`, `Card`, `Input`, `Table`, `Toast`, `Modal`, `Sparkline`, `ConfidenceMeter`, `Recorder`, `EmptyState`, `Skeleton`, `ErrorPanel`), each in `src/components/ui/`, with their states, before building routes.
3. One `api.ts` typed against the contract. Every fetch has abort, error mapping to the `ErrorPanel`.
4. Hindi/Marathi strings live in `strings.ts`; no Hindi inline in JSX except where specified as brand copy.
5. Do not add libraries beyond: react-router, leaflet, lucide-react. Charts are inline SVG.
6. Bundle target: under 400 KB gzipped JS for first load; Leaflet loaded lazily on `/officer` only.
7. Any deviation needed goes to `docs/CONTRACT_REQUESTS.md` with a one-line reason; the designer re-checks against section 9.
