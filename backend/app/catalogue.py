"""Brand and SKU matching.

Gemini proposes a `sku_id` (from the compact catalogue in the prompt) or null. This module
does not trust it blindly: every line is re-checked against the catalogue by exact alias
match, rapidfuzz similarity and a phonetic key built for Hinglish spelling, then given a
status (matched / uncertain / unknown), a combined confidence and up to three alternatives.
Nothing is silently corrected: a disagreement between Gemini and the catalogue makes the
line "uncertain" and says why.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from .models import Alternative, ModelOrderLine, OrderLine

# Combined confidence below this is "uncertain" and needs a clerk's eyes.
CONFIDENCE_THRESHOLD = 0.8
# Fuzzy match scores. Below MIN_SUGGEST the line is "unknown" (still lists alternatives >= MIN_ALT).
MIN_SUGGEST = 0.62
MIN_ALT = 0.45
# When Gemini named no item, the catalogue alone must be this sure before an item is suggested.
MIN_SUGGEST_UNNAMED = 0.75
# Two different SKUs scoring within this margin means the line is ambiguous.
AMBIGUITY_MARGIN = 0.04
SPELLING_MIN = 0.9  # plain (non-phonetic) spelling similarity below this is not "matched"
MODEL_WEIGHT = 0.4
MATCH_WEIGHT = 0.6

# Words that describe the quantity, not the product ("dolo 650 25 patte"). Removed before matching.
_UNIT_WORDS = frozenset({
    "strip", "strips", "patta", "patte", "pattay", "pata", "box", "boxes", "dabba", "dibba", "bottle", "bottles",
    "botal", "sachet", "sachets", "tube", "tubes", "vial", "vials", "nos", "pcs", "piece", "pieces",
    "पत्ते", "पत्ता", "पत्ती", "पट्ट्या", "पट्टी", "पैकेट", "डब्बा", "डिब्बा", "डब्बे", "बोतल", "बॉटल", "शीशी", "सैशे",
    "पाउच", "नग", "बाटली", "बाटल्या",
})
# Hinglish grammar and filler that carries no brand ("ondem ke 4", "bachchon wali ondem syrup"). Dropped before the
# spelling check so a clean Latin brand name inside a natural sentence is not marked uncertain for its grammar.
_FILLER_WORDS = frozenset({
    "ka", "ki", "ke", "ko", "wali", "wala", "vali", "waali", "bachchon", "bachon", "bacchon", "bachcho", "aur", "the",
    "a", "woh", "wo", "vo", "bhej", "dena", "de", "do", "please", "pls", "chahiye", "bhi", "zaroor", "bhejna",
})
# Words about availability, dropped before looking a "not available" mention up in the catalogue.
_STOCK_WORDS = frozenset({
    "nahi", "nahin", "nai", "short", "khatam", "not", "available", "out", "of", "stock", "na", "aaya", "aya", "pichli", "baar", "tha", "hai", "is", "zaroor", "bhejna", "confirm", "check", "kare", "karo", "chahiye", "mila",
})
_DEVANAGARI_RE = re.compile("[ऀ-ॿ]")
# Words that name a kind of medicine or a bit of Hinglish grammar, not a brand. They must not carry a match alone.
_GENERIC_WORDS = frozenset({
    "syrup", "syp", "suspension", "drops", "drop", "tablet", "tablets", "tab", "capsule", "cap", "injection", "inj",
    "cream", "ointment", "powder", "gel", "wali", "wala", "vali", "waali", "ka", "ki", "ke", "bachchon", "bachon",
    "bacchon", "bachcho", "ek", "do", "teen", "woh", "wo", "vo", "aur", "the", "a",
})
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_SPACE_RE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Lowercase, drop punctuation, collapse spaces. Keeps digits and Devanagari letters."""
    lowered = text.lower().replace("-", " ").replace("/", " ")
    # ऀ-ॿ keeps Devanagari vowel signs, which \w does not match.
    cleaned = re.sub(r"[^\w\s.ऀ-ॿ]", " ", lowered, flags=re.UNICODE).replace("_", " ")
    return _SPACE_RE.sub(" ", cleaned).strip()


_PHONETIC_RULES: tuple[tuple[str, str], ...] = (
    ("ph", "f"), ("ck", "k"), ("kh", "k"), ("gh", "g"), ("sh", "s"), ("ch", "c"),
    ("th", "t"), ("dh", "d"), ("bh", "b"), ("ee", "i"), ("oo", "u"), ("ou", "u"),
    ("q", "k"), ("x", "ks"), ("w", "v"), ("z", "s"), ("y", "i"),
)


def phonetic_key(text: str) -> str:
    """A consonant skeleton that survives Hinglish spelling drift.

    "krosin", "crocin" and "kroshin" all map near "krsn"; "pantop d" and "pan top d" agree.
    """
    s = normalise(text).replace(" ", "")
    for old, new in _PHONETIC_RULES:
        s = s.replace(old, new)
    s = re.sub(r"c(?=[eiy])", "s", s).replace("c", "k")
    if not s:
        return ""
    head, tail = s[0], re.sub(r"[aeiou]", "", s[1:])
    key = head + tail
    return re.sub(r"(.)\1+", r"\1", key)


def _numbers(text: str) -> set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUM_RE.findall(text)}


def _listed_words(tokens: list[str], names: list[str], sku: "Sku") -> bool:
    """True if every word and number written is a word of this item's brand, strength or a listed alias."""
    if not tokens:
        return False
    vocabulary = {t for n in names for t in n.split()} | set(normalise(sku.strength).split())
    return all(t in vocabulary for t in tokens)


@dataclass(frozen=True)
class Sku:
    sku_id: str
    brand: str
    strength: str
    form: str
    pack: str
    molecule: str
    group: str
    unit: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class _Entry:
    text: str
    phonetic: str
    numbers: frozenset[str]
    sku_id: str
    is_alias: bool


@dataclass(frozen=True)
class Candidate:
    sku_id: str
    score: float
    exact: bool


_SUGGESTED_REASON = "Gemini could not pick an item; the closest catalogue match is suggested."


class Catalogue:
    """In-memory catalogue with fast fuzzy lookup."""

    def __init__(self, rows: Iterable[dict[str, Any]]) -> None:
        self.skus: dict[str, Sku] = {}
        for row in rows:
            aliases = tuple(a.strip() for a in str(row.get("aliases", "")).split("|") if a.strip())
            sku = Sku(
                sku_id=row["sku_id"],
                brand=row["brand"],
                strength=row.get("strength", ""),
                form=row.get("form", ""),
                pack=row.get("pack", ""),
                molecule=row.get("molecule", ""),
                group=row.get("group", ""),
                unit=row.get("unit", ""),
                aliases=aliases,
            )
            self.skus[sku.sku_id] = sku
        self._entries: list[_Entry] = []
        self._exact: dict[str, set[str]] = {}
        for sku in self.skus.values():
            self._index(sku)

    def _index(self, sku: Sku) -> None:
        full = normalise(f"{sku.brand} {sku.strength}")
        names = [(normalise(sku.brand), False), (full, False), (normalise(f"{sku.brand} {sku.form}"), False)]
        names += [(normalise(a), True) for a in sku.aliases]
        for text, is_alias in names:
            if not text:
                continue
            self._entries.append(_Entry(text, phonetic_key(text), frozenset(_numbers(text)), sku.sku_id, is_alias))
            self._exact.setdefault(text, set()).add(sku.sku_id)

    # ------------------------------------------------------------------ views

    def get(self, sku_id: str | None) -> Sku | None:
        return self.skus.get(sku_id) if sku_id else None

    def prompt_table(self) -> str:
        """Compact catalogue for the Gemini prompt: one pipe-separated row per SKU.

        Token-lean: aliases that only repeat the brand (or brand + strength) are dropped, since the model already
        sees those. The table is identical on every call, which is what lets implicit caching reuse it.
        """
        lines = ["sku_id|brand|strength|form|aliases"]
        for s in self.skus.values():
            known = {normalise(s.brand), normalise(f"{s.brand} {s.strength}"),
                     normalise(f"{s.brand} {s.strength}".replace(" mg", "mg"))}
            kept: list[str] = []
            for alias in s.aliases:
                key = normalise(alias)
                if key not in known and key not in {normalise(k) for k in kept}:
                    kept.append(alias)
            lines.append(f"{s.sku_id}|{s.brand}|{s.strength}|{s.form}|{';'.join(kept)}")
        return "\n".join(lines)

    # ---------------------------------------------------------------- matching

    @staticmethod
    def _entry_score(query: str, query_phon: str, query_nums: set[str], entry: _Entry) -> float:
        base = max(fuzz.ratio(query, entry.text), fuzz.token_sort_ratio(query, entry.text)) / 100
        if len(entry.text) >= 5:
            base = max(base, 0.92 * fuzz.partial_ratio(query, entry.text) / 100)
        phon = 0.95 * fuzz.ratio(query_phon, entry.phonetic) / 100 if query_phon and entry.phonetic else 0.0
        score = max(base, phon)
        if query_nums and entry.numbers:
            score += 0.05 if query_nums & entry.numbers else -0.2
        return max(0.0, min(1.0, score))

    def rank(self, text: str, limit: int = 5) -> list[Candidate]:
        """Rank SKUs for a piece of free text, best first (one row per SKU)."""
        query = normalise(text)
        if not query:
            return []
        query_phon = phonetic_key(query)
        query_nums = _numbers(query)
        exact_ids = self._exact.get(query, set())
        best: dict[str, float] = {}
        for entry in self._entries:
            score = self._entry_score(query, query_phon, query_nums, entry)
            if entry.sku_id in exact_ids and entry.text == query:
                score = 1.0
            if score > best.get(entry.sku_id, 0.0):
                best[entry.sku_id] = score
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        unique = len(exact_ids) == 1  # an alias shared by several SKUs is not an exact match
        return [Candidate(sku_id=k, score=round(v, 3), exact=(unique and k in exact_ids)) for k, v in ranked]

    # -------------------------------------------------------------- validation

    def validate_line(self, line: ModelOrderLine) -> OrderLine:
        """Turn one Gemini line into a checked OrderLine. See module docstring for the rules."""
        spoken = line.raw_text
        if _DEVANAGARI_RE.search(spoken):
            # Brands are matched in Latin letters; a Devanagari transcription cannot be compared to the aliases.
            spoken = line.raw_text_latin or line.brand or line.raw_text
        query_parts = [spoken]
        if line.brand and normalise(line.brand) not in normalise(spoken):
            query_parts.append(line.brand)
        query = " ".join(query_parts)
        if line.strength and line.strength not in query:
            query = f"{query} {line.strength}"
        ranked = self._best_ranking(query, line.qty)
        model_conf = max(0.0, min(1.0, line.confidence))
        model_sku = self.get(line.sku_id)
        reasons: list[str] = []

        chosen: Candidate | None = None
        if model_sku is not None:
            own = next((c for c in ranked if c.sku_id == model_sku.sku_id), None)
            own_score = own.score if own else self._score_sku(query, model_sku.sku_id)
            top = ranked[0] if ranked else None
            chosen = Candidate(model_sku.sku_id, own_score, bool(own and own.exact))
            if top and top.sku_id != model_sku.sku_id and top.score - own_score > 0.1:
                reasons.append(
                    f"Gemini chose {model_sku.brand} {model_sku.strength} but the spelling is closer to "
                    f"{self.skus[top.sku_id].brand} {self.skus[top.sku_id].strength}."
                )
                own_score = min(own_score, CONFIDENCE_THRESHOLD - 0.05)
                chosen = Candidate(model_sku.sku_id, own_score, False)
        else:
            if line.sku_id:
                reasons.append("Gemini returned a code that is not in the catalogue; it was ignored.")
            top = ranked[0] if ranked else None
            untranslatable = bool(_DEVANAGARI_RE.search(spoken))  # no Latin spelling to compare with the aliases
            if top and top.score >= MIN_SUGGEST_UNNAMED and not untranslatable and self._names_a_brand(query, top):
                chosen = top
                reasons.append(_SUGGESTED_REASON)

        if chosen is None:
            alts = [] if _DEVANAGARI_RE.search(spoken) else self._alternatives(ranked, exclude=None)
            msg = "No catalogue item matches this wording. Pick one or leave it out."
            return OrderLine(
                raw_text=line.raw_text, qty=line.qty or 1, unit=line.unit, confidence=round(model_conf * 0.4, 2),
                status="unknown", alternatives=alts, reason=" ".join(reasons + [msg]),
            )

        # Ambiguity: a different SKU scores almost the same (for example Dolo 500 vs Dolo 650).
        runner_up = next((c for c in ranked if c.sku_id != chosen.sku_id), None)
        ambiguous = bool(runner_up and chosen.score - runner_up.score < AMBIGUITY_MARGIN and not chosen.exact)
        if ambiguous and runner_up:
            other = self.skus[runner_up.sku_id]
            reasons.append(f"Could also be {other.brand} {other.strength}; the strength was not clear.")

        sku = self.skus[chosen.sku_id]
        confidence = MODEL_WEIGHT * model_conf + MATCH_WEIGHT * chosen.score
        if ambiguous:
            confidence = min(confidence, CONFIDENCE_THRESHOLD - 0.05)
        confidence = self._cap_for_doubt(line, query, sku, chosen, confidence, reasons)
        if line.qty is None:
            reasons.append("Quantity was not stated; 1 is assumed.")
            confidence = min(confidence, CONFIDENCE_THRESHOLD - 0.05)
        confidence = round(max(0.0, min(1.0, confidence)), 2)
        status = "matched" if confidence >= CONFIDENCE_THRESHOLD else "uncertain"
        if status == "matched":  # the catalogue check resolved it confidently, so the "could not pick" note is moot
            reasons = [r for r in reasons if r != _SUGGESTED_REASON]
        if status == "uncertain" and not reasons:
            reasons.append("Confidence is below 80%; please check this line.")
        return OrderLine(
            raw_text=line.raw_text,
            sku_id=sku.sku_id,
            brand=sku.brand,
            strength=sku.strength,
            form=sku.form,
            molecule=sku.molecule,
            group=sku.group,
            qty=line.qty or 1,
            unit=line.unit if line.unit in {"strip", "box", "bottle", "sachet", "tube", "vial"} else sku.unit,
            confidence=confidence,
            status=status,
            alternatives=self._alternatives(ranked, exclude=sku.sku_id),
            reason=" ".join(reasons) or None,
        )

    def resolve_name(self, text: str) -> str | None:
        """The sku_id a free phrase clearly names ("electral nahi aaya"), or None. Used for 'not available' mentions."""
        cleaned = " ".join(t for t in normalise(text).split() if t not in _STOCK_WORDS)
        if not cleaned:
            return None
        ranked = self.rank(cleaned)
        top = ranked[0] if ranked else None
        if top and top.score >= MIN_SUGGEST_UNNAMED and self._names_a_brand(cleaned, top):
            return top.sku_id
        return None

    def _names_a_brand(self, query: str, top: Candidate) -> bool:
        """After dropping generic words (syrup, wali, ...), does what is left really resemble the suggested item?"""
        brandish = " ".join(t for t in normalise(query).split() if t not in _GENERIC_WORDS and t not in _UNIT_WORDS
                            and t not in _FILLER_WORDS and not t.isdigit())
        if not brandish:
            return False
        sku = self.skus[top.sku_id]
        names = [" ".join(t for t in normalise(n).split() if not t.isdigit() and t not in _GENERIC_WORDS)
                 for n in (sku.brand, *sku.aliases)]
        return max((fuzz.ratio(brandish, n) for n in names if n), default=0) / 100 >= SPELLING_MIN - 0.1

    def _cap_for_doubt(self, line: ModelOrderLine, query: str, sku: Sku, chosen: Candidate, confidence: float,
                       reasons: list[str]) -> float:
        """Keep a line out of "matched" when the wording only loosely fits the catalogue item.

        Nothing is silently corrected: a misspelling, a bare name shared by several items, or a model note that
        admits it interpreted the wording all send the line to the clerk with a reason.
        """
        cap = CONFIDENCE_THRESHOLD - 0.05
        tokens = [t for t in normalise(query).split()
                  if t not in _UNIT_WORDS and t not in _FILLER_WORDS and t != str(line.qty)]
        words = [t for t in tokens if not t.isdigit()]
        spelled = " ".join(tokens)
        names = [normalise(sku.brand), normalise(f"{sku.brand} {sku.strength}"), *(normalise(a) for a in sku.aliases)]
        plain = max((fuzz.ratio(spelled, n) for n in names if n), default=0) / 100
        if plain < SPELLING_MIN and _listed_words(tokens, names, sku):
            plain = 1.0  # every word and number is a listed word of this item, only in another order ("zinc 20 dt")
        if not chosen.exact and plain < SPELLING_MIN:
            reasons.append(f"Written as '{line.raw_text}', which is not a listed spelling of {sku.brand}; please confirm.")
            confidence = min(confidence, cap)
        elif words and not any(ch.isdigit() for ch in spelled):
            first = words[0]
            key = phonetic_key(first)
            siblings = [s for s in self.skus.values() if phonetic_key(normalise(s.brand).split()[0]) == key]
            if len(siblings) > 1 and normalise(sku.brand) != " ".join(words):
                reasons.append(
                    f"'{line.raw_text}' is only a bare name and {len(siblings)} catalogue items share it "
                    f"(for example {siblings[0].brand} and {siblings[1].brand}); check which one is meant.")
                confidence = min(confidence, cap)
        return confidence

    def _best_ranking(self, query: str, qty: int | None) -> list[Candidate]:
        """Rank the full wording and a version without quantity words and the ordered number.

        "ORS 20" means 20 sachets of ORS, not an item called ORS 20, so the cleaned wording is tried too and the
        better top score wins (the full wording keeps a real strength such as "Dolo 650" intact).
        """
        full = self.rank(query)
        tokens = [t for t in normalise(query).split() if t not in _UNIT_WORDS and t not in _FILLER_WORDS]
        if qty is not None and len(tokens) > 1:
            for i in range(len(tokens) - 1, -1, -1):
                if tokens[i] == str(qty):
                    del tokens[i]
                    break
        cleaned_query = " ".join(tokens)
        if not cleaned_query or cleaned_query == normalise(query):
            return full
        cleaned = self.rank(cleaned_query)
        if cleaned and (not full or cleaned[0].score >= full[0].score):
            return cleaned
        return full

    def _score_sku(self, query: str, sku_id: str) -> float:
        """Best entry score of one specific SKU against a query."""
        normalised = normalise(query)
        phon, nums = phonetic_key(normalised), _numbers(normalised)
        scores = [self._entry_score(normalised, phon, nums, e) for e in self._entries if e.sku_id == sku_id]
        return round(max(scores, default=0.0), 3)

    def _alternatives(self, ranked: list[Candidate], exclude: str | None) -> list[Alternative]:
        out: list[Alternative] = []
        for cand in ranked:
            if cand.sku_id == exclude or cand.score < MIN_ALT:
                continue
            sku = self.skus[cand.sku_id]
            out.append(Alternative(sku_id=sku.sku_id, brand=f"{sku.brand} {sku.strength}".strip(), score=cand.score))
            if len(out) == 3:
                break
        return out

    def enrich(self, line: OrderLine) -> OrderLine:
        """Fill brand, strength, form, molecule and group from the catalogue for a clerk-approved line."""
        sku = self.get(line.sku_id)
        if sku is None:
            return line
        return line.model_copy(
            update={
                "brand": sku.brand, "strength": sku.strength, "form": sku.form,
                "molecule": sku.molecule, "group": sku.group, "unit": line.unit or sku.unit,
            }
        )
