/** Hindi, Marathi and English strings for the ASHA flow. Marathi falls back to Hindi. */

export type AshaLang = "hi" | "mr";

interface Entry {
  hi: string;
  en: string;
  mr?: string;
}

export const ASHA_STRINGS = {
  todaysVisits: { hi: "आज के दौरे", en: "Today's visits" },
  chooseName: { hi: "अपना नाम चुनें", en: "Choose your name" },
  reportWithoutList: {
    hi: "सूची के बिना रिपोर्ट करें: अपनी जगह चुनें",
    en: "Report without a visit list: choose your locality",
    mr: "यादीशिवाय रिपोर्ट करा: तुमचा परिसर निवडा",
  },
  noVisits: {
    hi: "अभी कोई दौरा नहीं। जब अधिकारी सूची मंज़ूर करेंगे, वह यहाँ दिखेगी।",
    en: "No visits yet. When the officer approves a list it will appear here.",
  },
  refresh: { hi: "ताज़ा करें", en: "Refresh" },
  noInternet: { hi: "इंटरनेट नहीं है", en: "No internet" },
  retry: { hi: "फिर कोशिश करें", en: "Try again" },
  recordReport: { hi: "रिपोर्ट करें", en: "Record report" },
  speak: { hi: "बोलकर बताइए", en: "Speak" },
  promptCues: {
    hi: "कितने घर देखे? बुखार, दस्त, खाँसी वाले कितने? बच्चे कितने? पानी की कोई दिक्कत?",
    en: "How many homes? How many with fever, loose motions, cough? Children? Any water problem?",
    mr: "किती घरे पाहिली? ताप, जुलाब, खोकला किती? मुले किती? पाण्याची काही अडचण?",
  },
  tapStart: { hi: "दबाकर बोलना शुरू करें", en: "Tap to start", mr: "रेकॉर्डिंग सुरू करा" },
  tapStop: { hi: "रोकने के लिए दबाएँ", en: "Tap to stop" },
  recording: { hi: "रिकॉर्डिंग चल रही है", en: "Recording" },
  micDenied: {
    hi: "माइक्रोफ़ोन की अनुमति चाहिए। ब्राउज़र की सेटिंग में 'अनुमति दें' चुनें।",
    en: "We need the microphone. In your browser settings choose Allow.",
  },
  micMissing: {
    hi: "इस फ़ोन पर माइक्रोफ़ोन नहीं मिला। नीचे से फ़ाइल चुनें या लिखकर बताएँ।",
    en: "No microphone found. Upload a file or type instead.",
  },
  uploadFile: { hi: "फ़ाइल चुनें", en: "Upload an audio file" },
  typeInstead: { hi: "लिखकर बताएँ", en: "Type instead" },
  typePlaceholder: { hi: "यहाँ लिखें", en: "Write here" },
  recordAgain: { hi: "दोबारा रिकॉर्ड करें", en: "Record again" },
  send: { hi: "भेजें", en: "Send" },
  listening: { hi: "सुन रहे हैं...", en: "Listening" },
  sendFailed: { hi: "भेज नहीं पाए। आपकी रिकॉर्डिंग सुरक्षित है।", en: "Could not send. Your recording is kept." },
  isThisRight: { hi: "क्या यह सही है?", en: "Is this right?" },
  homes: { hi: "घर देखे", en: "Homes visited" },
  fever: { hi: "बुखार", en: "Fever" },
  diarrhoea: { hi: "दस्त", en: "Diarrhoea" },
  cough: { hi: "खाँसी", en: "Cough" },
  breathing: { hi: "साँस की दिक्कत", en: "Breathing" },
  rash: { hi: "चकत्ते", en: "Rash" },
  children: { hi: "बच्चे प्रभावित", en: "Children affected" },
  referred: { hi: "रेफर किए", en: "Referred" },
  water: { hi: "पानी की समस्या", en: "Water issue" },
  yes: { hi: "हाँ", en: "Yes" },
  no: { hi: "नहीं", en: "No" },
  edited: { hi: "बदला गया", en: "Edited" },
  whatYouSaid: { hi: "आपने कहा", en: "What you said" },
  showMore: { hi: "और दिखाएँ", en: "Show more" },
  showLess: { hi: "कम दिखाएँ", en: "Show less" },
  pleaseCheck: { hi: "यह जाँच लें", en: "Please check" },
  yesCorrect: { hi: "हाँ, सही है", en: "Yes, correct" },
  change: { hi: "बदलें", en: "Change" },
  saveChange: { hi: "सहेजें", en: "Save" },
  thankYou: { hi: "धन्यवाद!", en: "Thank you" },
  reportReceived: { hi: "आपकी रिपोर्ट मिल गई", en: "Report received", mr: "रिपोर्ट मिळाली" },
  alertForArea: { hi: "इस इलाके की चेतावनी", en: "Alert for this area" },
  strengthened: { hi: "पक्की हुई", en: "Confirmed" },
  weakened: { hi: "कमज़ोर हुई", en: "Weakened" },
  unchanged: { hi: "वैसी ही रही", en: "No big change" },
  noAlertChanged: { hi: "कोई चेतावनी नहीं बदली", en: "No alert changed" },
  nextVisit: { hi: "अगला दौरा", en: "Next visit" },
  backToList: { hi: "सूची पर वापस", en: "Back to list" },
  before: { hi: "पहले", en: "Before" },
  after: { hi: "अब", en: "Now" },
  priority: { hi: "प्राथमिकता", en: "Priority" },
  switchPerson: { hi: "नाम बदलें", en: "Not you?" },
  playback: { hi: "सुनें", en: "Play back" },
} satisfies Record<string, Entry>;

export type AshaKey = keyof typeof ASHA_STRINGS;

/** Primary text in her language, English beneath. */
export function tr(key: AshaKey, lang: AshaLang): { primary: string; secondary: string; lang: AshaLang } {
  const entry: Entry = ASHA_STRINGS[key];
  const primary = lang === "mr" ? (entry.mr ?? entry.hi) : entry.hi;
  return { primary, secondary: entry.en, lang: lang === "mr" && entry.mr ? "mr" : "hi" };
}

export const SYMPTOM_KEYS = ["fever", "diarrhoea", "cough", "breathing", "rash", "children", "referred"] as const;

export const SIMULATED_NOTICE = "Simulated demo data. Chemist orders and 90-day history are simulated, no real patients or people.";
