"""Catalogue matching: aliases, fuzzy spelling, phonetic Hinglish, unknowns, and honest uncertainty."""

from __future__ import annotations

from app.catalogue import CONFIDENCE_THRESHOLD, Catalogue, phonetic_key
from app.models import ModelOrderLine


def line(raw: str, sku: str | None = None, conf: float = 0.9, qty: int | None = 10, **kw) -> ModelOrderLine:
    return ModelOrderLine(raw_text=raw, sku_id=sku, confidence=conf, qty=qty, **kw)


def test_exact_alias_with_agreeing_model_is_matched(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("dolo 650", "S1"))
    assert result.status == "matched"
    assert result.sku_id == "S1"
    assert result.group == "fever"
    assert result.confidence >= CONFIDENCE_THRESHOLD
    assert result.reason is None


def test_spoken_alias_is_matched_without_model_help(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("dolo sau pachas", None, conf=0.9))
    assert result.sku_id == "S1"
    assert result.status in {"matched", "uncertain"}
    if result.status == "matched":
        assert "could not pick" not in (result.reason or "")
    else:
        assert "Gemini could not pick" in (result.reason or "")


def test_fuzzy_spelling_still_finds_the_item(fixture_catalogue: Catalogue) -> None:
    assert fixture_catalogue.rank("electrol")[0].sku_id == "S5"
    assert fixture_catalogue.rank("benadril syrup")[0].sku_id == "S9"


def test_phonetic_key_unites_hinglish_spellings() -> None:
    assert phonetic_key("krosin") == phonetic_key("crocin")
    assert phonetic_key("pan dee") != ""
    assert phonetic_key("") == ""


def test_phonetic_match_for_hinglish_spelling(fixture_catalogue: Catalogue) -> None:
    ranked = fixture_catalogue.rank("kroshin")
    assert ranked[0].sku_id == "S3"


def test_unknown_item_is_unknown_with_no_sku(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("zyxwvut forte", None, conf=0.4))
    assert result.status == "unknown"
    assert result.sku_id is None
    assert result.reason and "No catalogue item" in result.reason


def test_invented_sku_code_is_ignored_and_flagged(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("something odd qq", "S999", conf=0.9))
    assert result.sku_id is None
    assert result.status == "unknown"
    assert "not in the catalogue" in (result.reason or "")


def test_ambiguous_strength_is_uncertain_not_guessed_silently(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("dolo", "S1", conf=0.95))
    assert result.status == "uncertain"
    assert "Could also be" in (result.reason or "")
    assert result.alternatives and result.alternatives[0].sku_id == "S2"


def test_model_choice_that_disagrees_with_spelling_is_uncertain(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("electral", "S4", conf=0.95))
    assert result.status == "uncertain"
    assert "closer to" in (result.reason or "")
    assert any(a.sku_id == "S5" for a in result.alternatives)


def test_missing_quantity_assumes_one_and_says_so(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("crocin", "S3", qty=None))
    assert result.qty == 1
    assert result.status == "uncertain"
    assert "Quantity was not stated" in (result.reason or "")


def test_alternatives_are_at_most_three_and_exclude_the_choice(fixture_catalogue: Catalogue) -> None:
    result = fixture_catalogue.validate_line(line("pan", None, conf=0.5))
    assert len(result.alternatives) <= 3
    assert result.sku_id not in {a.sku_id for a in result.alternatives}


def test_prompt_table_lists_every_sku(fixture_catalogue: Catalogue) -> None:
    table = fixture_catalogue.prompt_table().splitlines()
    assert table[0].startswith("sku_id|brand")
    assert len(table) == 1 + len(fixture_catalogue.skus)


def test_real_catalogue_exact_names(real_catalogue: Catalogue) -> None:
    for sku in list(real_catalogue.skus.values())[:25]:
        result = real_catalogue.validate_line(line(f"{sku.brand} {sku.strength}", sku.sku_id, conf=0.95))
        assert result.sku_id == sku.sku_id


def test_ordered_quantity_is_not_mistaken_for_a_strength(real_catalogue: Catalogue) -> None:
    """Regression from the first live run: "ORS 20" must be ORS x20, not Omez 20."""
    ors = real_catalogue.validate_line(line("ORS 20", "SKU0021", qty=20, unit="sachet"))
    assert ors.sku_id == "SKU0021" and ors.status == "matched" and ors.qty == 20
    norflox = real_catalogue.validate_line(line("Norflox-TZ 15 patte", "SKU0023", qty=15, unit="strip"))
    assert norflox.sku_id == "SKU0023" and norflox.status == "matched"
    dolo = real_catalogue.validate_line(line("Dolo 650 25 patte", "SKU0001", qty=25, unit="strip"))
    assert dolo.sku_id == "SKU0001" and dolo.status == "matched"


def test_devanagari_quantity_words_are_ignored_and_marks_survive(real_catalogue: Catalogue) -> None:
    from app.catalogue import normalise

    assert normalise("पट्ट्या") == "पट्ट्या"
    marathi = real_catalogue.validate_line(line("Norflox-TZ 20 पट्ट्या", "SKU0023", qty=20, unit="strip"))
    assert marathi.status == "matched" and marathi.sku_id == "SKU0023"


def test_devanagari_without_latin_is_unknown_not_a_nonsense_guess(real_catalogue: Catalogue) -> None:
    line = real_catalogue.validate_line(ModelOrderLine(raw_text="बच्चों वाली सिरप", qty=2, confidence=0.3))
    assert line.status == "unknown" and line.sku_id is None and not line.alternatives


def test_devanagari_with_latin_spelling_matches_on_the_latin(real_catalogue: Catalogue) -> None:
    first = next(iter(real_catalogue.skus.values()))
    line = real_catalogue.validate_line(
        ModelOrderLine(raw_text="जिंकोविट", raw_text_latin=first.brand, sku_id=first.sku_id, qty=5, confidence=0.9))
    assert line.sku_id == first.sku_id and "closer to" not in (line.reason or "")


def test_misspelling_is_never_green(real_catalogue: Catalogue) -> None:
    first = next(iter(real_catalogue.skus.values()))
    garbled = first.brand[:-2] + "zq"
    line = real_catalogue.validate_line(ModelOrderLine(raw_text=garbled, sku_id=first.sku_id, qty=5, confidence=0.99))
    assert line.status != "matched"


def test_generic_word_overlap_is_not_a_brand_match(real_catalogue: Catalogue) -> None:
    line = real_catalogue.validate_line(
        ModelOrderLine(raw_text="बच्चों वाली सिरप 2 बोतल", raw_text_latin="Bachchon wali syrup", qty=2, confidence=0.2))
    assert line.status == "unknown" and line.sku_id is None


def test_bare_family_name_is_flagged_even_when_an_alias_matches(real_catalogue: Catalogue) -> None:
    line = real_catalogue.validate_line(ModelOrderLine(raw_text="calpol syp", sku_id="SKU0010", qty=6, confidence=0.95))
    assert line.status == "uncertain" and "share it" in (line.reason or "")


def test_matched_lines_do_not_carry_the_could_not_pick_reason(fixture_catalogue: Catalogue) -> None:
    for spoken in ("dolo sau pachas", "dolo 650", "electral"):
        result = fixture_catalogue.validate_line(line(spoken, None, conf=0.95))
        if result.status == "matched":
            assert "could not pick" not in (result.reason or "")
