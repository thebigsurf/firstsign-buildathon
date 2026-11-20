"""Order parsing (voice, photo, text) and ASHA report parsing.

Live path: Gemini structured output, then catalogue validation.
Offline path (DEMO_OFFLINE=1 or no key): canned data/samples/*.expected.json by filename
or hash, and a small rule-based reader for free text, so the demo never dies.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .catalogue import Catalogue
from .errors import BadRequest, UpstreamError
from .gemini import GeminiClient, GeminiResult, Media
from .models import AshaStructured, ModelOrderLine, ModelOrderOut, OrderLine, ParsedOrder

log = logging.getLogger("firstsign.parsing")

MAX_MEDIA_BYTES = 20 * 1024 * 1024

_MIME_BY_SUFFIX = {
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg",
    ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".webm": "audio/webm",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic",
}

ORDER_SYSTEM = """You are the order desk assistant of an Indian medicine distributor. A chemist (shop owner) sent a \
WhatsApp voice note, a photo of a handwritten list, or a text message. It may be in Hindi, Marathi, English or a mix \
(Hinglish). Your job is to read it faithfully and turn it into order lines.

Rules:
1. Return one line per medicine the chemist wants to order. Copy the chemist's own words for the line into raw_text.
2. sku_id must be copied EXACTLY from the catalogue below, or be null. Never invent a sku_id. If you are not sure \
which catalogue item is meant, return null and keep what you heard in raw_text.
3. qty is the number of units the chemist asked for, as an integer. If no quantity is said or written, return null. \
unit is one of: strip, box, bottle, sachet, tube, vial, or null.
4. confidence is your honest 0 to 1 confidence in the line. Use a low value when the audio is unclear, the \
handwriting is hard to read, or two catalogue items could fit.
5. not_available: list anything the chemist says was short, out of stock, did not arrive, or asks you to confirm is \
available (for example "Azithral nahi aaya"). Do not turn those into order lines unless he also orders them.
6. transcript: for audio, the words spoken (keep Hindi in Devanagari or Roman as spoken). For a photo, the text you \
read, line by line.
7. language: the main language, as hi, mr or en.
8. Never include any patient name. Do not guess. Do not correct the chemist's choices.
9. If raw_text is in Devanagari (or any non-Latin script), also give raw_text_latin: the medicine name in Latin letters as it would be printed on the pack (for example "Zincovit", "ORS", "Pan D").
10. List in unplaced every word or number you heard or read that looks like part of an order but that you could not turn into a line. If you had to interpret an unclear word, name it in notes. Never drop a line silently.
"""

ASHA_SYSTEM = """You structure a voice note from an ASHA worker (community health worker in India) about a household \
visit round. The note may be in Hindi, Marathi or English. Return counts only.

Rules:
1. households_visited: how many households she visited. fever, diarrhoea, cough, breathing (breathing difficulty), \
rash: how many people had that symptom, as integers. 0 if she did not mention it.
2. children_affected: how many of those were children. referred: how many she referred to a health facility.
3. water_issue_reported: true only if she mentions dirty, smelly, contaminated or interrupted water, or a pipeline \
leak or sewage problem.
4. transcript: her words, faithfully. language: hi, mr or en.
5. notes: one short sentence of anything useful that is not a count. NEVER include any person's name, phone number or \
house number.
"""


@dataclass(frozen=True)
class Upload:
    """A file received over HTTP."""

    data: bytes
    filename: str
    content_type: str | None = None


def _looks_like(mime: str, head: bytes) -> bool:
    """Check the first bytes of a file against the signature of its claimed type (no Gemini call is wasted on junk)."""
    if mime == "audio/wav":
        return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if mime == "audio/mpeg":
        return head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    if mime == "audio/aac":
        return len(head) > 1 and head[0] == 0xFF and head[1] & 0xF0 == 0xF0
    if mime == "audio/ogg":
        return head[:4] == b"OggS"
    if mime == "audio/flac":
        return head[:4] == b"fLaC"
    if mime == "audio/webm":
        return head[:4] == bytes([0x1A, 0x45, 0xDF, 0xA3])
    if mime in {"audio/mp4", "image/heic"}:
        return head[4:8] == b"ftyp"
    if mime == "image/jpeg":
        return head[:3] == bytes([0xFF, 0xD8, 0xFF])
    if mime == "image/png":
        return head[:8] == bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    if mime == "image/webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return True


def detect_mime(upload: Upload, kinds: tuple[str, ...]) -> str:
    """Work out the mime type from the file extension, then the declared content type."""
    suffix = Path(upload.filename or "").suffix.lower()
    mime = _MIME_BY_SUFFIX.get(suffix)
    if mime is None and upload.content_type:
        declared = upload.content_type.split(";")[0].strip().lower()
        if declared.startswith(("audio/", "image/")):
            mime = declared
    if mime is None or not mime.startswith(tuple(f"{k}/" for k in kinds)):
        allowed = " or ".join(kinds)
        raise BadRequest(f"Unsupported file. Please upload {allowed} (for example .ogg, .mp3, .wav, .jpg, .png).")
    if not upload.data:
        raise BadRequest("The uploaded file is empty.")
    if len(upload.data) > MAX_MEDIA_BYTES:
        raise BadRequest("The file is larger than 20 MB. Please send a shorter note.")
    if not _looks_like(mime, upload.data[:16]):
        raise BadRequest(
            f"This file is not a real {mime.split('/')[0]} file: its contents do not match its type. "
            "Please upload a genuine recording or photo.",
            code="invalid_media",
        )
    return mime


def prepare_audio(data: bytes, mime: str) -> tuple[bytes, str]:
    """Browser recordings arrive as WebM/MP4; convert to OGG/Opus when ffmpeg is on the PATH."""
    if mime not in {"audio/webm", "audio/mp4"} or not shutil.which("ffmpeg"):
        return data, mime
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-c:a", "libopus", "-f", "ogg", "pipe:1"],
            input=data, capture_output=True, timeout=30, check=True,
        )
        return proc.stdout, "audio/ogg"
    except (subprocess.SubprocessError, OSError):
        log.warning("ffmpeg conversion failed; sending the original audio")
        return data, mime


# ------------------------------------------------------------------ order parsing


def _order_prompt(catalogue: Catalogue, chemist: dict[str, Any], kind: str, text: str | None) -> str:
    language = {"hi": "Hindi", "mr": "Marathi", "en": "English"}.get(chemist.get("language", ""), "Hindi")
    source = f"Message text from the chemist:\n{text}" if text else f"The attached file is a {kind}."
    return (
        f"The chemist usually writes or speaks {language}.\n{source}\n\n"
        f"CATALOGUE (sku_id|brand|strength|form|aliases):\n{catalogue.prompt_table()}"
    )


_UNITS = r"(strips?|boxe?s?|bottles?|sachets?|tubes?|vials?|patta|pattay|dabba|dibba|botal|bottle)"
_UNIT_MAP = {"patta": "strip", "pattay": "strip", "dabba": "box", "dibba": "box", "botal": "bottle"}
_SHORT_RE = re.compile(r"\b(nahi|nahin|nai|short|khatam|not available|out of stock|na aaya|nahi aaya)\b", re.I)
_QTY_UNIT_RE = re.compile(rf"(\d+)\s*{_UNITS}\b", re.I)
_X_QTY_RE = re.compile(r"\bx\s*(\d+)\b|\b(\d+)\s*x\b", re.I)


def rule_based_lines(text: str) -> ModelOrderOut:
    """Offline reader for plain text orders. Deliberately conservative: low confidence."""
    lines: list[ModelOrderLine] = []
    unavailable: list[str] = []
    for segment in re.split(r"[\n,;]+|\s+aur\s+|\s+and\s+|\s*\+\s*", text):
        segment = segment.strip(" .-")
        if not segment:
            continue
        if _SHORT_RE.search(segment):
            unavailable.append(segment)
            continue
        qty: int | None = None
        unit: str | None = None
        cleaned = segment
        m = _QTY_UNIT_RE.search(segment)
        if m:
            qty, unit = int(m.group(1)), m.group(2).lower().rstrip("s")
            cleaned = segment.replace(m.group(0), " ")
        else:
            m = _X_QTY_RE.search(segment)
            if m:
                qty = int(m.group(1) or m.group(2))
                cleaned = segment.replace(m.group(0), " ")
        unit = _UNIT_MAP.get(unit or "", unit)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            lines.append(ModelOrderLine(raw_text=cleaned, qty=qty, unit=unit, confidence=0.6))
    return ModelOrderOut(language="en", transcript=text, lines=lines, not_available=unavailable,
                         notes="Read by the offline rule-based reader (no Gemini call).")


def coerce_order_output(expected: dict[str, Any]) -> ModelOrderOut:
    """Accept either a raw model-style answer or a ParsedOrder-shaped expected file."""
    lines = []
    for item in expected.get("lines", []):
        lines.append(
            ModelOrderLine(
                raw_text=str(item.get("raw_text") or item.get("text") or item.get("brand") or "").strip() or "?",
                sku_id=item.get("sku_id"),
                brand=item.get("brand"),
                strength=item.get("strength"),
                qty=item.get("qty"),
                unit=item.get("unit"),
                confidence=float(item.get("confidence", 0.9)),
            )
        )
    return ModelOrderOut(
        language=str(expected.get("language", "hi")),
        transcript=str(expected.get("transcript", "")),
        lines=lines,
        not_available=[str(x) for x in expected.get("not_available", [])],
        notes=str(expected.get("notes", "")),
    )


UNAVAILABLE_NOTE = (
    "Gemini was unavailable just now, so this is the pre-recorded reading of this demo sample, not a live result."
)


_INTERPRET_RE = re.compile(r"interpret|assum|guess|probably|likely|presum|unclear|ambiguous|could be|may be|might", re.I)
_QUOTED_RE = re.compile(r"['\"‘“]([^'\"’”]+)['\"’”]")
_DIGITS_RE = re.compile(r"\d+")


def _quoted_in(said: str, notes: str) -> bool:
    """True if a word quoted in a note sentence that admits interpretation is a whole word of this line."""
    words = set(re.findall(r"\w+", said))
    for sentence in re.split(r"(?<=[.!?])\s+", notes):
        if _INTERPRET_RE.search(sentence):
            for quote in _QUOTED_RE.findall(sentence):
                if len(quote) >= 3 and set(re.findall(r"\w+", quote.lower())) <= words:
                    return True
    return False


def _flag_interpreted(lines: list[OrderLine], notes: str) -> list[OrderLine]:
    """A line the model's own notes say it had to interpret cannot stay green."""
    if not notes or not _INTERPRET_RE.search(notes):
        return lines
    lowered = notes.lower()
    out: list[OrderLine] = []
    for line in lines:
        said = line.raw_text.strip().lower()
        if line.status == "matched" and len(said) >= 3 and (said in lowered or _quoted_in(said, notes)):
            reason = "The reader noted it had to interpret this line; please confirm."
            line = line.model_copy(update={
                "status": "uncertain", "confidence": min(line.confidence, 0.75),
                "reason": f"{line.reason} {reason}".strip() if line.reason else reason,
            })
        out.append(line)
    return out


def _missing_line_warning(out: ModelOrderOut, line_count: int) -> str:
    """Words the model could not place, or more numbers in a typed/read text than lines found."""
    parts: list[str] = []
    if out.unplaced:
        parts.append("Heard but not placed in any line: " + ", ".join(out.unplaced) + ".")
    elif out.language and len(_DIGITS_RE.findall(out.transcript)) > 2 * max(line_count, 1) + 1:
        parts.append("The text has more numbers than order lines; a line may be missing.")
    if parts:
        parts.append("Please check nothing is missing.")
    return " ".join(parts)


def _canned_order(gemini: GeminiClient, upload: Upload | None, hint: dict[str, Any] | None) -> dict[str, Any] | None:
    """The bundled answer for a demo sample (by inbox hint, content hash or filename), if there is one."""
    if hint is not None:
        return hint
    return gemini.offline_samples.lookup(upload.filename, upload.data) if upload is not None else None


def _expected_lines(catalogue: Catalogue, canned: dict[str, Any]) -> list[OrderLine] | None:
    """The bundled reading's lines exactly as designed (statuses, alternatives, reasons), enriched from the catalogue.

    Returns None when the bundled file has no final statuses, so the lines are then checked like a live reading.
    """
    raw = canned.get("lines", [])
    if not raw or not all("status" in item for item in raw):
        return None
    lines = []
    for item in raw:
        line = OrderLine.model_validate({k: v for k, v in item.items() if k in OrderLine.model_fields})
        lines.append(catalogue.enrich(line) if line.sku_id else line)
    return lines


def _read_live(gemini: GeminiClient, catalogue: Catalogue, chemist: dict[str, Any], upload: Upload | None,
               text: str | None) -> tuple[ModelOrderOut, GeminiResult]:
    media: list[Media] = []
    kind = "text message"
    if upload is not None:
        mime = detect_mime(upload, ("audio", "image"))
        data, mime = prepare_audio(upload.data, mime) if mime.startswith("audio/") else (upload.data, mime)
        media.append(Media(data=data, mime_type=mime, filename=upload.filename))
        kind = "voice note" if mime.startswith("audio/") else "photo of a handwritten order list"
    prompt = _order_prompt(catalogue, chemist, kind, text.strip() if text else None)
    result = gemini.generate_structured(
        gemini.settings.model_fast, prompt, ModelOrderOut, media=media, system=ORDER_SYSTEM, fast=True
    )
    try:
        return ModelOrderOut.model_validate(result.json()), result
    except ValueError as exc:
        raise UpstreamError("Gemini returned an order in an unexpected shape.") from exc


def parse_order(
    gemini: GeminiClient,
    catalogue: Catalogue,
    chemist: dict[str, Any],
    *,
    message_id: str | None = None,
    upload: Upload | None = None,
    text: str | None = None,
    expected_hint: dict[str, Any] | None = None,
) -> ParsedOrder:
    """Parse one chemist message into a ParsedOrder.

    `expected_hint` is the bundled answer for an inbox sample. It is used only in offline mode, or when Gemini is
    down and the input is a known demo sample (the result is then labelled as pre-recorded, never passed off as live).
    """
    if not upload and not (text and text.strip()):
        raise BadRequest("Send an audio file, a photo, or some text to parse.")
    started = time.perf_counter()
    cached = False
    canned_lines: list[OrderLine] | None = None

    if gemini.offline:
        canned = _canned_order(gemini, upload, expected_hint)
        if canned is not None:
            out, model_name = coerce_order_output(canned), "offline-sample"
            canned_lines = _expected_lines(catalogue, canned)
        elif text:
            out, model_name = rule_based_lines(text), "offline-rules"
        else:
            out = ModelOrderOut(notes="Offline demo mode: this file is not one of the bundled samples, so it was not read.")
            model_name = "offline-none"
        latency = int((time.perf_counter() - started) * 1000)
    else:
        try:
            out, result = _read_live(gemini, catalogue, chemist, upload, text)
            model_name, latency, cached = result.model, result.latency_ms, result.cached
        except UpstreamError:
            canned = _canned_order(gemini, upload, expected_hint)
            if canned is None:
                raise
            out, model_name, latency = coerce_order_output(canned), "offline-sample", 0
            canned_lines = _expected_lines(catalogue, canned)
            out = out.model_copy(update={"notes": f"{UNAVAILABLE_NOTE} {out.notes}".strip()})

    if canned_lines is not None:
        lines = canned_lines
    else:
        lines = _flag_interpreted([catalogue.validate_line(line) for line in out.lines], out.notes)
        warning = _missing_line_warning(out, len(lines))
        if warning:
            out = out.model_copy(update={"notes": f"{out.notes} {warning}".strip()})
    return ParsedOrder(
        message_id=message_id,
        chemist_id=chemist["chemist_id"],
        language=out.language if out.language in {"hi", "mr", "en"} else chemist.get("language", "hi"),
        transcript=out.transcript,
        lines=lines,
        not_available=out.not_available,
        notes=out.notes,
        model=model_name,
        latency_ms=latency,
        cached=cached,
    )


# ------------------------------------------------------------------ ASHA reports

_ASHA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fever": ("bukhar", "bukhaar", "बुखार", "ताप", "fever"),
    "diarrhoea": ("dast", "दस्त", "जुलाब", "loose motion", "diarrhoea", "diarrhea"),
    "cough": ("khansi", "खांसी", "खोकला", "cough"),
    "breathing": ("saans", "सांस", "breathing", "breathless"),
    "rash": ("daane", "दाने", "rash", "खाज"),
    "children_affected": ("bacche", "बच्चे", "children", "kids", "mule", "मुले"),
    "referred": ("refer", "रेफर"),
    "households_visited": ("ghar", "घर", "household", "houses", "families"),
}
_WATER_WORDS = ("gande pani", "गंदा पानी", "dirty water", "smelly water", "pani ki problem", "पाणी", "sewage", "pipeline")


def rule_based_asha(text: str) -> AshaStructured:
    """Offline reader for a typed ASHA note: finds a number next to each symptom word."""
    lowered = text.lower()
    values: dict[str, int] = {}
    for field_name, words in _ASHA_KEYWORDS.items():
        for word in words:
            m = re.search(rf"(\d+)\s*(?:\w+\s){{0,2}}{re.escape(word)}|{re.escape(word)}\s*(?:\w+\s){{0,2}}?(\d+)", lowered)
            if m:
                values[field_name] = int(m.group(1) or m.group(2))
                break
    return AshaStructured(
        language="en",
        transcript=text,
        water_issue_reported=any(w in lowered for w in _WATER_WORDS),
        notes="Read by the offline rule-based reader (no Gemini call).",
        **values,
    )


@dataclass(frozen=True)
class ParsedAsha:
    report: AshaStructured
    model: str
    latency_ms: int


def parse_asha_report(
    gemini: GeminiClient,
    asha: dict[str, Any],
    *,
    upload: Upload | None = None,
    text: str | None = None,
) -> ParsedAsha:
    """Structure an ASHA voice note or text into counts.

    Like order parsing, a known demo recording falls back to its bundled reading (labelled) if Gemini is down.
    """
    if not upload and not (text and text.strip()):
        raise BadRequest("Record or upload a voice note, or type the report.")
    started = time.perf_counter()
    canned = gemini.offline_samples.lookup(upload.filename, upload.data) if upload else None
    if gemini.offline:
        elapsed = int((time.perf_counter() - started) * 1000)
        if canned is not None:
            return ParsedAsha(AshaStructured.model_validate(canned), "offline-sample", elapsed)
        if text:
            return ParsedAsha(rule_based_asha(text), "offline-rules", elapsed)
        raise BadRequest("Offline demo mode can only read the bundled sample recordings or typed text.")

    media: list[Media] = []
    if upload is not None:
        mime = detect_mime(upload, ("audio",))
        data, mime = prepare_audio(upload.data, mime)
        media.append(Media(data=data, mime_type=mime, filename=upload.filename))
    language = {"hi": "Hindi", "mr": "Marathi", "en": "English"}.get(asha.get("language", ""), "Hindi")
    prompt = f"The ASHA usually speaks {language}. " + (
        f"Her typed report:\n{text}" if text else "The attached recording is her report."
    )
    try:
        result = gemini.generate_structured(
            gemini.settings.model_fast, prompt, AshaStructured, media=media, system=ASHA_SYSTEM, fast=True
        )
    except UpstreamError:
        if canned is None:
            raise
        report = AshaStructured.model_validate(canned)
        return ParsedAsha(report.model_copy(update={"notes": f"{UNAVAILABLE_NOTE} {report.notes}".strip()}),
                          "offline-sample", 0)
    try:
        report = AshaStructured.model_validate(result.json())
    except ValueError as exc:
        raise UpstreamError("Gemini returned an ASHA report in an unexpected shape.") from exc
    return ParsedAsha(report, result.model, result.latency_ms)
