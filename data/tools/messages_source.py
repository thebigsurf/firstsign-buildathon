"""Ground truth for the demo inbox and the ASHA voice reports.

Line tuple: (raw_text, sku_key | None, qty, status, alternatives)
where alternatives is a list of (sku_key, score). A "matched" line has no
alternatives; "uncertain" and "unknown" lines list the plausible candidates so
the clerk can pick one. Quantities use the catalogue unit unless noted.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class Line(TypedDict):
    raw: str
    key: Optional[str]
    qty: int
    status: str
    unit: Optional[str]
    alts: list[tuple[str, float]]
    conf: float


def L(raw: str, key: Optional[str], qty: int, status: str = "matched", alts: Optional[list[tuple[str, float]]] = None,
      conf: Optional[float] = None, unit: Optional[str] = None) -> Line:
    default = {"matched": 0.95, "uncertain": 0.55, "unknown": 0.2}[status]
    return {"raw": raw, "key": key, "qty": qty, "status": status, "unit": unit,
            "alts": alts or [], "conf": default if conf is None else conf}


# Each order message: id, chemist pick (pin, wanted language), type, media filename, language, transcript,
# lines, not_available, notes, received time (IST, 20 Nov 2026), plain text for text messages.
ORDERS: list[dict] = [
    {
        "id": "msg_01", "pin": "400070", "lang": "hi", "type": "voice", "media": "order_01.mp3", "time": "07:12",
        "transcript": "भैया सुबह का ऑर्डर लिख लो। ओ आर एस बीस, इलेक्ट्रल दस, नॉरफ्लॉक्स टीज़ेड पंद्रह पत्ते, "
                      "ओन्डेम चार दस पत्ते, मेट्रोजिल चार सौ दस पत्ते, और डोलो छह सौ पचास पच्चीस पत्ते भेज देना।",
        "lines": [
            L("o r s", "ors", 20), L("electral", "electral", 10), L("norflox tz", "norfloxtz", 15),
            L("ondem 4", "ondem4", 10), L("metrogyl 400", "metrogyl400", 10), L("dolo 650", "dolo650", 25),
        ],
        "not_available": [], "notes": "Mostly diarrhoea-group items in one order.",
    },
    {
        "id": "msg_02", "pin": "400022", "lang": "hi", "type": "voice", "media": "order_02.mp3", "time": "07:31",
        "transcript": "सुनो, आज का माल लिखो। पैन डी दस पत्ते, ओ आर एस पचास, रेडोटिल सौ वाला पंद्रह पत्ते, "
                      "ज़िंकोविट पाँच पत्ते, शेल्कल पाँच पत्ते। और वो बच्चों वाली सिरप दो बोतल भेज देना।",
        "lines": [
            L("pan dee", "pand", 10, "uncertain", [("pand", 0.55), ("pantopd", 0.30), ("pan40", 0.10)]),
            L("o r s", "ors", 50), L("redotil 100", "redotil100", 15), L("zincovit", "zincovit", 5),
            L("shelcal", "shelcal500", 5),
            L("woh bachchon wali syrup", None, 2, "unknown",
              [("calpol120", 0.25), ("dolo120", 0.22), ("crocinds", 0.18)], unit="bottle"),
        ],
        "not_available": [],
        "notes": "Two lines need the clerk: 'pan dee' (Pan-D or Pantop-D) and the unnamed children's syrup.",
    },
    {
        "id": "msg_03", "pin": "400022", "lang": "mr", "type": "voice", "media": "order_03.mp3", "time": "07:48",
        "transcript": "दादा, उद्याची ऑर्डर लिहून घ्या. ओ आर एस चाळीस, नॉरफ्लॉक्स टीझेड वीस पट्ट्या, "
                      "ओन्डेम चार पंधरा पट्ट्या, इलेक्ट्रल पंधरा. स्पोर्लॅक गेल्या वेळी आलं नव्हतं, ते यावेळी पाठवा, दहा. "
                      "आणि क्रोसिन सहाशे पन्नास दहा पट्ट्या.",
        "lines": [
            L("o r s", "ors", 40), L("norflox tz", "norfloxtz", 20), L("ondem 4", "ondem4", 15),
            L("electral", "electral", 15), L("sporlac", "sporlac", 10), L("crocin 650", "crocin650", 10),
        ],
        "not_available": ["Sporlac (sender says it did not arrive last time)"],
        "notes": "Marathi voice note. Sporlac was short in the last delivery and is asked for again.",
    },
    {
        "id": "msg_04", "pin": "400024", "lang": "hi", "type": "voice", "media": "order_04.mp3", "time": "08:05",
        "transcript": "भैया ऑर्डर लिखिए। सिनारेस्ट दस पत्ते, एस्कोरिल एल एस पाँच बोतल, मॉन्टेयर एल सी बीस पत्ते, "
                      "कैंडिड क्रीम छह, और सेट्ज़ीन दस पत्ते। अज़िथ्रल पाँच सौ वाला भी आठ पत्ते भेजना।",
        "lines": [
            L("sinarest", "sinarest", 10), L("ascoril ls", "ascorills", 5), L("montair lc", "montairlc", 20),
            L("candid cream", "candid", 6), L("cetzine", "cetzine10", 10), L("azithral 500", "azithral500", 8),
        ],
        "not_available": [], "notes": "Routine cough, cold and allergy order.",
    },
    {
        "id": "msg_05", "pin": "400022", "lang": "hi", "type": "photo", "media": "order_05.jpg", "time": "08:20",
        "transcript": "ORS   30\nNorflox TZ   20\nOndem 4   20\nElectral   15\nZincovit   5\nPan 40   10",
        "lines": [
            L("ORS", "ors", 30), L("Norflox TZ", "norfloxtz", 20), L("Ondem 4", "ondem4", 20),
            L("Electral", "electral", 15), L("Zincovit", "zincovit", 5), L("Pan 40", "pan40", 10),
        ],
        "not_available": [], "notes": "Handwritten chit, clear writing.", "language": "en",
    },
    {
        "id": "msg_06", "pin": "400017", "lang": "hi", "type": "photo", "media": "order_06.jpg", "time": "08:34",
        "transcript": "Dolo 650   20\nAzithral 500   10\nAugmentin 625   8\nMontair LC   10\nAsthalin inhaler   5\nCalpol syp   6",
        "lines": [
            L("Dolo 650", "dolo650", 20), L("Azithral 500", "azithral500", 10), L("Augmentin 625", "augmentin625", 8),
            L("Montair LC", "montairlc", 10), L("Asthalin inhaler", "asthalin", 5),
            L("Calpol syp", "calpol120", 6, "uncertain",
              [("calpol120", 0.45), ("calpol250", 0.30), ("dolo120", 0.10)]),
        ],
        "not_available": [],
        "notes": "'Calpol syp' could be the 120 mg or the 250 mg suspension; the clerk must choose.",
        "language": "en",
    },
    {
        "id": "msg_07", "pin": "400088", "lang": "hi", "type": "photo", "media": "order_07.jpg", "time": "08:47",
        "transcript": "Dolo 650   50\nCrocin 650   30\nPCM 500   40\nMeftal P syp   12\nORSL orange   10\nLimcee   10\n"
                      "[struck out] Avil 25   5",
        "lines": [
            L("Dolo 650", "dolo650", 50), L("Crocin 650", "crocin650", 30),
            L("PCM 500", "pcm500", 40, "uncertain",
              [("pcm500", 0.60), ("crocinadv500", 0.18), ("dolo500", 0.12), ("pacimol500", 0.10)]),
            L("Meftal P syp", "meftalp", 12), L("ORSL orange", "orslorange", 10), L("Limcee", "limcee500", 10),
        ],
        "not_available": [],
        "notes": "The last line (Avil 25) is crossed out by the sender, so it is not an order line. "
                 "Fever-medicine heavy order.",
        "language": "en",
    },
    {
        "id": "msg_08", "pin": "400070", "lang": "hi", "type": "text", "media": None, "time": "08:52",
        "text": "bhai ors 25 aur electral 12 bhej dena, norflox tz 10 strip, ondem 4 ke 8 patte. "
                "kal ka payment friday ko kar dunga",
        "transcript": "bhai ors 25 aur electral 12 bhej dena, norflox tz 10 strip, ondem 4 ke 8 patte. "
                      "kal ka payment friday ko kar dunga",
        "lines": [
            L("ors", "ors", 25), L("electral", "electral", 12), L("norflox tz", "norfloxtz", 10),
            L("ondem 4", "ondem4", 8),
        ],
        "not_available": [], "notes": "The payment promise is a remark, not an order item.",
    },
    {
        "id": "msg_09", "pin": "400037", "lang": "hi", "type": "text", "media": None, "time": "09:03",
        "text": "Sir aaj ka order: ors 30, electral 10, metrogyl 400 12 patta, zinc 20 dt 15 strip, sporlac 10 sachet. "
                "sporlac pichli baar short tha, is baar zaroor bhejna. bachchon wali ondem syrup 6 bottle",
        "transcript": "Sir aaj ka order: ors 30, electral 10, metrogyl 400 12 patta, zinc 20 dt 15 strip, sporlac 10 sachet. "
                      "sporlac pichli baar short tha, is baar zaroor bhejna. bachchon wali ondem syrup 6 bottle",
        "lines": [
            L("ors", "ors", 30), L("electral", "electral", 10), L("metrogyl 400", "metrogyl400", 12),
            L("zinc 20 dt", "zinc20", 15), L("sporlac", "sporlac", 10), L("ondem syrup", "ondemsyr", 6),
        ],
        "not_available": ["Sporlac (sender says it was short last time)"],
        "notes": "Sporlac was short in the previous delivery; the sender asks for it again.",
    },
    {
        "id": "msg_10", "pin": "400043", "lang": "hi", "type": "text", "media": None, "time": "09:11",
        "text": "Dolo 650 30 strip, crocin 650 20, pacimol 650 20 aur orsl orange 12 bottle bhej do",
        "transcript": "Dolo 650 30 strip, crocin 650 20, pacimol 650 20 aur orsl orange 12 bottle bhej do",
        "lines": [
            L("dolo 650", "dolo650", 30), L("crocin 650", "crocin650", 20), L("pacimol 650", "pacimol650", 20),
            L("orsl orange", "orslorange", 12),
        ],
        "not_available": [], "notes": "Fever-medicine order.",
    },
]

# ASHA reports. asha pick by (pin), locality by name within that pin.
ASHA_REPORTS: list[dict] = [
    {
        "file": "asha_01.mp3", "asha_id": "ASHA03", "pin": "400024", "locality": "Bhim Nagar", "language": "hi",
        "transcript": "आज भीम नगर में चौदह घर गई। पाँच घरों में दस्त और उल्टी, तीन बच्चे हैं, एक को अस्पताल भेजा। "
                      "लोग कह रहे हैं पानी गंदा आ रहा है।",
        "households_visited": 14, "fever": 0, "diarrhoea": 5, "cough": 0, "breathing": 0, "rash": 0,
        "children_affected": 3, "referred": 1, "water_issue_reported": True,
        "notes": "Vomiting along with diarrhoea. Residents say the supplied water looks dirty.",
    },
    {
        "file": "asha_02.mp3", "asha_id": "ASHA05", "pin": "400022", "locality": "Pratiksha Nagar", "language": "mr",
        "transcript": "आज मी प्रतीक्षा नगरमध्ये पंधरा घरांना भेट दिली. आठ घरांत जुलाब आणि उलट्या आहेत, चार लहान मुले आहेत. "
                      "दोन जणांना सायन रुग्णालयात पाठवले. नळाचे पाणी पिवळसर येत आहे असे लोक सांगतात.",
        "households_visited": 15, "fever": 0, "diarrhoea": 8, "cough": 0, "breathing": 0, "rash": 0,
        "children_affected": 4, "referred": 2, "water_issue_reported": True,
        "notes": "Diarrhoea and vomiting. Residents say tap water is yellowish. Two people sent to Sion hospital.",
    },
    {
        "file": "asha_03.mp3", "asha_id": "ASHA11", "pin": "400086", "locality": "Asalpha", "language": "hi",
        "transcript": "आज असल्फा में बारह घर गई। सब ठीक है। दो घरों में हल्की खाँसी है, दस्त या बुखार किसी को नहीं। "
                      "पानी साफ आ रहा है।",
        "households_visited": 12, "fever": 0, "diarrhoea": 0, "cough": 2, "breathing": 0, "rash": 0,
        "children_affected": 0, "referred": 0, "water_issue_reported": False,
        "notes": "Nothing unusual. Two households with mild cough. Water is clean.",
    },
    {
        "file": "asha_04.mp3", "asha_id": "ASHA09", "pin": "400088", "locality": "Lallubhai Compound", "language": "hi",
        "transcript": "आज लल्लूभाई कंपाउंड में सोलह घर गई। छह घरों में बुखार है, दो बच्चों को तेज़ बुखार और बदन दर्द है, "
                      "एक को अस्पताल भेजा। खाँसी नहीं है। आसपास पानी जमा है और मच्छर बहुत हैं।",
        "households_visited": 16, "fever": 6, "diarrhoea": 0, "cough": 0, "breathing": 0, "rash": 0,
        "children_affected": 2, "referred": 1, "water_issue_reported": False,
        "notes": "High fever with body ache, no cough. Stagnant water nearby and many mosquitoes.",
    },
]
