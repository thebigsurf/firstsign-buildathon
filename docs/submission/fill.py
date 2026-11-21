from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

IMG = 'docs/deck_img/'  # screenshots used in the deck
DOCS = 'docs/'
INK = RGBColor(0x20, 0x21, 0x24); GREY = RGBColor(0x5F, 0x63, 0x68); BLUE = RGBColor(0x1A, 0x73, 0xE8)
GREEN = RGBColor(0x18, 0x80, 0x38); AMBER = RGBColor(0xB0, 0x60, 0x00)
LBLUE = RGBColor(0xE8, 0xF0, 0xFE); LGREEN = RGBColor(0xE6, 0xF4, 0xEA); LAMB = RGBColor(0xFE, 0xF7, 0xE0); LGREY = RGBColor(0xF1, 0xF3, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = 'Google Sans Flex'
p = Presentation(DOCS + 'submission/template.pptx')
S = p.slides


def tb(slide, x, y, w, h, paras, size=12):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); f = t.text_frame; f.word_wrap = True
    f.margin_left = f.margin_right = Inches(0.04); f.margin_top = f.margin_bottom = Inches(0.02)
    first = True
    for para in paras:
        pr = f.paragraphs[0] if first else f.add_paragraph(); first = False
        pr.space_after = Pt(5)
        for style, txt in para:
            r = pr.add_run(); r.text = txt; r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = INK
            if 'b' in style: r.font.bold = True
            if 'g' in style: r.font.color.rgb = GREY
            if 'B' in style: r.font.color.rgb = BLUE
            if 'G' in style: r.font.color.rgb = GREEN
            if 'L' in style: r.font.size = Pt(size + 3)
    return t


def box(slide, x, y, w, h, title, body='', fill=LBLUE, line=BLUE, size=11):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.12
    s.fill.solid(); s.fill.fore_color.rgb = fill; s.line.color.rgb = line; s.line.width = Pt(1.25)
    f = s.text_frame; f.word_wrap = True; f.vertical_anchor = MSO_ANCHOR.MIDDLE
    f.margin_left = f.margin_right = Inches(0.06)
    pr = f.paragraphs[0]; pr.alignment = PP_ALIGN.CENTER
    r = pr.add_run(); r.text = title; r.font.bold = True; r.font.size = Pt(size); r.font.color.rgb = INK; r.font.name = FONT
    if body:
        q = f.add_paragraph(); q.alignment = PP_ALIGN.CENTER
        r = q.add_run(); r.text = body; r.font.size = Pt(size - 2); r.font.color.rgb = GREY; r.font.name = FONT
    return s


def arrow(slide, x, y, w=0.28, h=0.22, kind=MSO_SHAPE.RIGHT_ARROW):
    a = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid(); a.fill.fore_color.rgb = BLUE; a.line.fill.background(); return a


def img(slide, path, x, y, w=None, h=None):
    kw = {}
    if w: kw['width'] = Inches(w)
    if h: kw['height'] = Inches(h)
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)
    pic.line.color.rgb = RGBColor(0xDA, 0xDC, 0xE0); pic.line.width = Pt(0.75)
    return pic


def table(slide, x, y, w, rows, colw, size=10):
    n = len(rows); m = len(rows[0])
    t = slide.shapes.add_table(n, m, Inches(x), Inches(y), Inches(w), Inches(0.3 * n)).table
    for j, cw in enumerate(colw): t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.text = ''
            c.margin_left = c.margin_right = Inches(0.06); c.margin_top = c.margin_bottom = Inches(0.03)
            r = c.text_frame.paragraphs[0].add_run(); r.text = val; r.font.size = Pt(size); r.font.name = FONT
            r.font.color.rgb = WHITE if i == 0 else INK; r.font.bold = (i == 0 or j == 0)
            c.fill.solid(); c.fill.fore_color.rgb = BLUE if i == 0 else (LGREY if i % 2 == 0 else WHITE)
    return t


# slide 1: title with team details
t = S[1].shapes[1]; t.width = Inches(5.0); t.height = Inches(2.0); t.top = Inches(3.3)
f = t.text_frame; f.clear(); f.word_wrap = True
lines = [('Team Name: ', 'FirstSign'), ('Team Size: ', '2 (Utkarsh Tiwari, Sourav Dasgupta)'),
         ('Problem Statement: ', 'Illness shows up first as medicine orders at the chemist, but those orders reach distributors as WhatsApp voice notes and handwritten lists that are retyped by hand and never read for what they reveal.')]
for k, (a, b) in enumerate(lines):
    pr = f.paragraphs[0] if k == 0 else f.add_paragraph(); pr.space_after = Pt(6)
    r = pr.add_run(); r.text = a; r.font.bold = True; r.font.size = Pt(12); r.font.name = FONT; r.font.color.rgb = INK
    r = pr.add_run(); r.text = b; r.font.size = Pt(12); r.font.name = FONT; r.font.color.rgb = INK

# slide 2: brief
s = S[2]
tb(s, 0.35, 1.3, 9.3, 1.1, [[('bL', 'FirstSign is the medicine distributor’s AI order desk that sees illness first.')],
                            [('g', 'Chemists keep ordering the way they do today. Gemini turns their voice notes and handwritten-list photos into ready-to-bill orders, flags what it is unsure of, and a clerk approves. The same approved orders become a pin-code illness signal, checked on the ground by ASHA workers.')]], size=13)
items = [('1  Order desk', 'Voice, photo and text orders in Hindi, Marathi and Hinglish become ready-to-bill lines matched to the catalogue.', LBLUE, BLUE),
         ('2  Stock radar', 'The distributor sees which medicine groups are rising in which pin codes, and what to stock.', LGREEN, GREEN),
         ('3  Health officer', 'Alerts with a Gemini explanation (Google Search grounded) and a drafted, ranked ASHA visit list.', LAMB, AMBER),
         ('4  ASHA loop', 'ASHAs report by voice in their own language; two raised reports confirm an alert.', LGREY, GREY)]
for k, (a, b, fl, ln) in enumerate(items):
    box(s, 0.35 + k * 2.35, 2.6, 2.2, 1.75, a, b, fill=fl, line=ln, size=12)
tb(s, 0.35, 4.55, 9.3, 0.8, [[('b', 'Design for blame: '), ('', 'unsure lines turn yellow, nothing is corrected silently, every approval is logged with a name, and AI only drafts; a person sends.')]], size=12)

# slide 3: opportunities
s = S[3]
tf = s.shapes[0].text_frame; tf.clear(); r = tf.paragraphs[0].add_run(); r.text = 'Opportunities'; r.font.size = Pt(24); r.font.name = FONT; r.font.color.rgb = INK
s.shapes[0].height = Inches(0.6)
qa = [('How different is it from existing ideas?', 'Marg and Pharmarack connect software to software. Many small chemists have no software; they send a voice note or a photo. We read those, keep an audit trail of who approved each line, and add an illness layer by pin code that no ordering tool offers.'),
      ('How will it solve the problem?', 'The clerk stops retyping and stops carrying silent errors; the owner sees stock-outs and rising demand; the health office gets an early, explained, ground-checked alert instead of waiting for case reports.'),
      ('USP of the proposed solution', 'One pipe, two values: the distributor pays for a faster, safer order desk, and the illness signal rides along. Every correction by a clerk, an ASHA or a doctor (via our Dischargely product) is a signed label; that is the moat, because reading itself gets cheaper with every Gemini release.')]
y = 1.35
for q, a in qa:
    tb(s, 0.35, y, 9.3, 1.2, [[('bB', q)], [('', a)]], size=12); y += 1.32

# slide 4: features
s = S[4]
left = [('Reads voice notes', 'Hindi, Marathi, Hinglish audio to order lines'), ('Reads handwritten lists', 'photo to lines; crossed-out items kept off the bill'), ('Catalogue matching with abstention', 'a SKU or “unknown”, never a guess; unsure lines yellow'), ('Clerk approval and audit log', 'every edit and approval with a name and time'), ('Chemist send screen', 'WhatsApp-style send: voice, photo or text'), ('Role sign-in', 'clerk, owner, officer, ASHA, chemist and founder workspaces')]
right = [('Stock radar', 'rising groups by pin code, stock-outs, days of cover, what to stock'), ('Pin-code signal', '28-day normal, breadth across chemists, chronic baseline, decoy suppression'), ('Gemini agent', 'likely causes with confidence, Google Search grounding, drafted notes and ASHA visit list'), ('ASHA voice reports', 'structured into counts, no names; 2 reports confirm'), ('Back-test and context', 'simulated back-test panel; real weather and air (Open-Meteo)'), ('Resilience', 'model fallback, caching, labelled offline replay; Hindi-first, phone-first UI')]
for xs, lst in [(0.35, left), (5.05, right)]:
    tb(s, xs, 1.3, 4.55, 4.1, [[('b', '•  ' + a + ': '), ('g', b)] for a, b in lst], size=12)

# slide 5: process flow
s = S[5]
r1 = [('Chemist sends', 'voice note, photo or text on WhatsApp'), ('Gemini reads', 'transcribes, matches catalogue, flags unsure lines'), ('Clerk approves', 'fixes yellow lines; audit log'), ('Order billed', 'ready-to-bill order')]
r2 = [('Pin-code signal', 'vs 28-day normal, breadth across shops'), ('Alert + agent', 'Gemini explains with Search grounding, drafts actions'), ('Officer approves', 'ranked ASHA visit list'), ('ASHA voice report', 'Hindi/Marathi; 2 reports confirm')]
W = 2.0; G = 0.35
for k, (a, b) in enumerate(r1):
    box(s, 0.35 + k * (W + G), 1.45, W, 1.15, a, b, fill=LBLUE, line=BLUE, size=12)
    if k < 3: arrow(s, 0.35 + k * (W + G) + W + 0.035, 1.92)
for k, (a, b) in enumerate(r2):
    box(s, 0.35 + k * (W + G), 3.3, W, 1.15, a, b, fill=LGREEN if k < 2 else LAMB, line=GREEN if k < 2 else AMBER, size=12)
    if k < 3: arrow(s, 0.35 + k * (W + G) + W + 0.035, 3.77)
arrow(s, 0.35 + 2 * (W + G) + 0.85, 2.68, 0.3, 0.55, MSO_SHAPE.DOWN_ARROW)
tb(s, 0.35 + 2 * (W + G) + 1.2, 2.7, 3.2, 0.55, [[('g', 'approved orders roll up into counts by pin code and medicine group')]], size=10)
box(s, 0.35, 4.62, 4.35, 0.62, 'Distributor stock radar', 'what is rising, stock-outs, what to stock', fill=LGREY, line=GREY, size=11)
box(s, 5.05, 4.62, 4.3, 0.62, 'Feedback loop', 'ASHA outcomes label alerts; precision measured', fill=LGREY, line=GREY, size=11)

# slide 6: wireframes / mocks
s = S[6]
img(s, IMG + 'p_chemist.png', 0.35, 1.3, h=3.75)
img(s, IMG + 'p_inbox.png', 2.25, 1.3, w=5.4)
img(s, IMG + 'p_asha.png', 7.85, 1.3, h=3.75)
tb(s, 2.25, 4.8, 5.4, 0.5, [[('b', 'Chemist send → distributor inbox → ASHA report. '), ('g', 'Live screens; data simulated and labelled.')]], size=11)

# slide 7: architecture
s = S[7]
users = ['Chemist (phone)', 'Distributor clerk / owner (web)', 'Health officer (web)', 'ASHA (phone, Hindi/Marathi)']
tb(s, 0.3, 1.25, 1.9, 0.3, [[('bB', 'Users')]], size=12)
for k, u in enumerate(users): box(s, 0.3, 1.6 + k * 0.88, 1.9, 0.72, u, fill=LGREY, line=GREY, size=11)
arrow(s, 2.27, 2.85, 0.3, 0.3)
cr = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.65), Inches(1.25), Inches(3.55), Inches(3.95)); cr.adjustments[0] = 0.04
cr.fill.solid(); cr.fill.fore_color.rgb = WHITE; cr.line.color.rgb = BLUE; cr.line.width = Pt(2)
tb(s, 2.75, 1.3, 3.4, 0.3, [[('bB', 'Google Cloud Run · asia-south1 (Mumbai)')]], size=11)
for k, (a, b) in enumerate([('React + TypeScript web app', '4 role workspaces, phone-first'), ('FastAPI backend', 'parsing · catalogue matcher · audit log'), ('Signal engine', 'pin-code baselines, breadth, alerts'), ('Agent orchestrator', 'grounded search step → reasoning step')]):
    box(s, 2.8, 1.68 + k * 0.86, 3.25, 0.72, a, b, size=11)
arrow(s, 6.27, 2.85, 0.3, 0.3)
gm = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.65), Inches(1.25), Inches(3.05), Inches(2.6)); gm.adjustments[0] = 0.05
gm.fill.solid(); gm.fill.fore_color.rgb = LGREEN; gm.line.color.rgb = GREEN; gm.line.width = Pt(2)
tb(s, 6.75, 1.3, 2.9, 0.3, [[('bG', 'Gemini API (google-genai)')]], size=11)
box(s, 6.8, 1.68, 2.75, 0.95, 'Gemini Flash', 'audio · vision · structured JSON; fallback 3.5 → 3.8 → 3.1-flash-lite', fill=WHITE, line=GREEN, size=11)
box(s, 6.8, 2.75, 2.75, 0.95, 'Gemini reasoning model', '+ Google Search grounding; explains alerts, drafts actions', fill=WHITE, line=GREEN, size=11)
for k, (a, b) in enumerate([('Secret Manager', 'API key'), ('Cloud Build + Artifact Registry', 'image'), ('Firestore · BigQuery', 'built, off by default')]):
    box(s, 6.65, 3.98 + k * 0.42, 3.05, 0.37, a + '  ·  ' + b, fill=LGREY, line=GREY, size=9)

# slide 8: technologies
s = S[8]
rows = [['Layer', 'Technology', 'Why'],
        ['AI', 'Gemini Flash family (3.5 / 3.8 / 3.1-flash-lite), Gemini reasoning model', 'audio, vision, schema output; reasoning for the agent'],
        ['Grounding', 'Google Search grounding tool in the Gemini API', 'outside context for alerts'],
        ['Backend', 'Python 3.11, FastAPI, Pydantic v2, google-genai SDK, rapidfuzz', 'typed, schema-checked JSON'],
        ['Frontend', 'React 18, TypeScript, Vite, Tailwind, Leaflet + OpenStreetMap', 'phone-first, accessible, bilingual'],
        ['Cloud', 'Cloud Run (asia-south1), Secret Manager, Cloud Build, Artifact Registry', 'serverless; key never in code'],
        ['Data (optional)', 'Firestore, BigQuery AI.FORECAST', 'designed behind flags, off by default'],
        ['Context data', 'Open-Meteo weather and air quality (real)', 'heat and rain context for alerts'],
        ['Quality', 'pytest (132), Vitest (41), ESLint, tsc, Playwright, axe-core', 'tested end to end']]
table(s, 0.35, 1.35, 9.3, rows, [1.4, 4.6, 3.3], size=10.5)

# slide 9: cost
s = S[9]
rows = [['Item', 'Estimate', 'Basis'],
        ['Price to a distributor', '₹3,000–4,500 per desk per month', 'our estimate; tested in the pilot'],
        ['Our cost per order', '₹0.4–0.7, mostly human checking', 'our estimate'],
        ['Gemini per order', '₹0.25 (measured, AI only)', '20 live calls on Gemini 3.5 Flash; token ledger'],
        ['Cloud Run', 'one always-on instance', '₹1,000 budget alert set'],
        ['Chemist', 'free', 'no new app'],
        ['Public-health pilot', '₹25 lakh–2 Cr per district', 'grant or CSR funded; our estimate'],
        ['Dischargely (live revenue)', '₹10–15 lakh setup + ~₹2 lakh/month per hospital', 'our live hospital contract; funds the FirstSign pilot']]
table(s, 0.35, 1.35, 9.3, rows, [2.4, 3.4, 3.5], size=11)
tb(s, 0.35, 4.6, 9.3, 0.7, [[('b', 'Year 3 (est.): '), ('', '10 hospitals on Dischargely ≈ ₹2.4 Cr recurring + ~₹1.25 Cr setup; 250 distributors on FirstSign ≈ ₹1.35 Cr; ≈ ₹5 Cr combined before any grant.')]], size=12)

# slide 10: snapshots
s = S[10]
shots = [(IMG + 'p_officer.png', 'Health officer: map and alerts'), (IMG + 'p_agent.png', 'Gemini explanation and drafted actions'), (IMG + 'p_radar.png', 'Distributor stock radar and stock-outs'), (DOCS + 'auth_screens/login_1440.png', 'Sign-in with role workspaces')]
for k, (pth, cap) in enumerate(shots):
    x = 0.35 + (k % 2) * 4.7; y = 1.3 + (k // 2) * 2.05
    img(s, pth, x, y, w=2.75)
    tb(s, x + 2.85, y + 0.4, 1.7, 1.0, [[('b', cap)]], size=11)

# slide 11: performance
s = S[11]
rows = [['Measure', 'Result', 'How measured'],
        ['Order lines read right', '55 of 56 (98%)', '10 sample orders: 4 voice, 3 photo, 3 text; gemini-3.1-flash-lite'],
        ['Wrong lines shown as certain', '0', 'same run; doubt goes yellow instead'],
        ['Parse latency', '4.6 s median, 7.2 s p95', '20 live calls on gemini-3.5-flash'],
        ['ASHA report fields right', '35 of 36', '4 voice reports: Hindi ×3, Marathi ×1'],
        ['Alert explanation', '~31–37 s cold, 0.1 s cached', 'Search-grounded step + reasoning step; 4–7 sources'],
        ['Signal back-test', 'both seeded events alert; decoy suppressed', 'simulated history, labelled as such'],
        ['AI cost', '₹0.25 per order, ₹0.05 per ASHA report', 'usage ledger; ~68% of prompt tokens cached']]
table(s, 0.35, 1.35, 9.3, rows, [2.4, 2.6, 4.3], size=10.5)
tb(s, 0.35, 4.75, 9.3, 0.5, [[('g', 'Small sample made for the test; the pilot measures accuracy on real orders (clerk edit rate) and alert precision against ASHA findings.')]], size=10)

# slide 12: future
s = S[12]
L = [('90-day Mumbai pilot', '5 distributors around Kurla and Sion, 1 ward health office, 10 ASHAs; pass marks set before we start'), ('Billing write-back', 'approved orders straight into Marg and other billing software'), ('WhatsApp Business API', 'orders arrive without a forward or upload step'), ('Vertex AI', 'service-account auth, provisioned throughput, evals on real clerk edits')]
R = [('Cloud-native data', 'Firestore for state, BigQuery AI.FORECAST for baselines (designed, to switch on)'), ('More languages', 'Gujarati, Bengali, Tamil voice orders'), ('Labels from Dischargely', 'doctor-confirmed medicine–diagnosis pairs teach what a rise means'), ('Published precision', 'lead time and false alarms against ASHA findings, every season')]
for xs, lst in [(0.35, L), (5.05, R)]:
    tb(s, xs, 1.3, 4.55, 4.0, [[('b', '•  ' + a + ': '), ('g', b)] for a, b in lst], size=12)

# slide 13: business model
s = S[13]
tb(s, 0.28, 0.73, 9.0, 0.6, [[('', 'Business model and go-to-market')]], size=24)
rows = [['Who', 'Gets', 'Pays'], ['Distributor (buyer)', 'Order desk that frees part of a clerk; stock radar', '₹3,000–4,500 / month per desk (est.)'], ['Chemist', 'Orders billed right, faster; no new app', 'Free'], ['Health office / CSR', 'Ranked ASHA visits, confirmed alerts', 'District pilot, grant funded (est.)'], ['Hospitals (Dischargely, live)', 'Discharge summaries in 10–15 min, not 30–40', '₹10–15 lakh setup + ~₹2 lakh / month']]
table(s, 0.35, 1.45, 9.3, rows, [2.2, 4.2, 2.9], size=11)
tb(s, 0.35, 3.55, 9.3, 1.7, [[('b', 'Runway: '), ('', 'Dischargely hospital revenue funds the FirstSign pilot; year 3 ≈ ₹5 Cr combined (est.: 10 hospitals + 250 distributors).')], [('b', 'Go-to-market: '), ('', 'start with distributors who already take WhatsApp orders; three free trials in Mumbai, ask for payment on day 30.')], [('b', 'Open signal: '), ('', 'no exclusive partner; we charge for measurement and proof, never for exclusivity.')], [('b', 'Weakest assumptions, tested first: '), ('', 'will a distributor pay; how slow the desk is today (time 20 real orders); does the signal hold (blind back-test on a known outbreak).')]], size=12)

# slide 14: team and links
s = S[14]
tb(s, 0.28, 0.73, 9.0, 0.6, [[('', 'Team, proof and links')]], size=24)
tb(s, 0.35, 1.45, 4.55, 3.8, [[('bB', 'Why us')], [('b', 'Dischargely: '), ('', 'our live hospital product; discharge summaries in 10–15 min instead of 30–40, paid for today.')], [('b', '3rd place, Andhra Pradesh health-surveillance hackathon: '), ('', 'disease tracking from ~10,000 coded outpatient records; the ASHA voice report started there.')], [('b', 'Team: '), ('', 'Utkarsh Tiwari, Sourav Dasgupta.')]], size=12)
tb(s, 5.05, 1.45, 4.6, 3.8, [[('bB', 'Try it')], [('b', 'Live: '), ('', 'firstsign-735269146498.asia-south1.run.app')], [('b', 'Sign in: '), ('', 'any account on the sign-in page, password “firstsign”')], [('b', 'Code: '), ('', 'github.com/thebigsurf/firstsign-buildathon')], [('b', 'Data: '), ('g', 'chemists, orders and history are simulated and labelled on every screen; weather and air are real (Open-Meteo).')]], size=12)

img(S[14], IMG + 'dx_volume.png', 0.35, 3.5, w=4.4)
tb(S[14], 0.35, 4.6, 4.5, 0.3, [[('g', 'Dischargely: weekly summaries in our live hospital, Jun–Sep 2026')]], size=9)

# drop the instruction slide
ids = p.slides._sldIdLst; first = list(ids)[0]
p.part.drop_rel(first.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')); ids.remove(first)
p.save(DOCS + 'submission/FirstSign_Final_Submission.pptx'); print('saved', len(p.slides))
