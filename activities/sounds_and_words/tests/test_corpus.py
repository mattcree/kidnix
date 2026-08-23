"""The corpus itself: shape, provenance, and internal consistency.

A corpus that quietly disagrees with itself is worse than no corpus, because
the ceiling is only as trustworthy as the segmentations it gates on.
"""

from __future__ import annotations

import pytest

from sounds_and_words.ceiling import segment, tokenise
from sounds_and_words.corpus import load_corpus

PHASE_2_SETS = {
    1: ["s", "a", "t", "p"],
    2: ["i", "n", "m", "d"],
    3: ["g", "o", "c", "k"],
    4: ["ck", "e", "u", "r"],
    5: ["h", "b", "f", "ff", "l", "ll", "ss"],
}
PHASE_3_SETS = {6: ["j", "v", "w", "x"], 7: ["y", "z", "zz", "qu"]}
PHASE_3_DIGRAPHS = ["ch", "sh", "th", "ng"]
PHASE_3_VOWELS = [
    "ai", "ee", "igh", "oa", "oo", "ar", "or", "ur", "ow", "oi", "ear", "air", "ure", "er",
]


# --------------------------------------------------------------------- loading
def test_corpus_loads():
    c = load_corpus()
    assert c.gpcs and c.words and c.tricky_words and c.sentences and c.texts


def test_load_corpus_is_cached():
    assert load_corpus() is load_corpus()


def test_counts_are_what_the_readme_claims(corpus):
    assert len(corpus.gpcs) == 114
    assert len(corpus.untaught) == 15
    assert len(corpus.words) == 846
    assert len(corpus.tricky_words) == 56
    assert len(corpus.sentences) == 119
    assert len(corpus.texts) == 5


# ------------------------------------------------------------ the progression
@pytest.mark.parametrize("set_no,graphemes", sorted(PHASE_2_SETS.items()))
def test_phase_2_sets_are_in_the_right_order(corpus, set_no, graphemes):
    got = [g.grapheme for g in corpus.gpcs
           if g.phase == 2 and g.set == set_no and g.added_by is None and g.variant_of is None]
    assert got == graphemes


@pytest.mark.parametrize("set_no,graphemes", sorted(PHASE_3_SETS.items()))
def test_phase_3_sets_are_in_the_right_order(corpus, set_no, graphemes):
    got = [g.grapheme for g in corpus.gpcs if g.phase == 3 and g.set == set_no]
    assert got == graphemes


def test_phase_3_consonant_digraphs_come_before_the_vowel_graphemes(corpus):
    by_id = corpus.gpc_by_id
    assert all(by_id[d].order < by_id["ai"].order for d in PHASE_3_DIGRAPHS)


def test_every_phase_3_vowel_grapheme_is_present(corpus):
    graphemes = {g.grapheme for g in corpus.gpcs if g.phase == 3}
    for v in PHASE_3_VOWELS:
        assert v in graphemes, v


def test_phase_4_introduces_no_new_gpcs(corpus):
    """L&S Phase Four is adjacent consonants and new tricky words, nothing else."""
    assert [g for g in corpus.gpcs if g.phase == 4] == []
    assert any(w.phase == 4 for w in corpus.words)
    assert any(t.phase == 4 for t in corpus.tricky_words)


def test_phase_5_is_present_and_marked(corpus):
    p5 = [g for g in corpus.gpcs if g.phase == 5]
    assert len(p5) > 40
    assert any(g.alternative_pronunciation for g in p5)
    assert any(g.split for g in p5)


def test_orders_are_monotonic_by_phase(corpus):
    for a, b in zip(corpus.gpcs, corpus.gpcs[1:], strict=False):
        assert a.order <= b.order
        assert a.phase <= b.phase


def test_gpc_ids_are_unique(corpus):
    ids = [g.id for g in corpus.gpcs]
    assert len(ids) == len(set(ids))


def test_split_digraphs_are_marked_split(corpus):
    for g in corpus.gpcs:
        if "-" in g.grapheme:
            assert g.split is True
            assert g.kind == "split_digraph"


def test_multigraph_kinds_match_their_length(corpus):
    lengths = {"single": 1, "digraph": 2, "trigraph": 3, "doubled": 2, "quadgraph": 4}
    for g in corpus.gpcs:
        if g.kind in lengths and not g.split:
            assert len(g.grapheme) == lengths[g.kind], g.id


# ---------------------------------------------------------------- provenance
def test_every_gpc_cites_a_source(corpus):
    for g in corpus.gpcs:
        assert g.source, g.id


def test_every_word_cites_a_source(corpus):
    for w in corpus.words:
        assert w.source


def test_kidnix_additions_are_all_marked(corpus):
    added = [g for g in corpus.gpcs if not g.from_letters_and_sounds]
    assert {g.id for g in added} == {
        "bb", "dd", "gg", "mm", "nn", "pp", "rr", "tt", "or_er"
    }
    for g in added:
        assert g.added_by == "kidnix"
        assert g.note


def test_sources_toml_records_the_ogl(corpus):
    ids = {s["id"] for s in corpus.sources["source"]}
    assert {"ls2007", "reading_framework_2023"} <= ids
    for s in corpus.sources["source"]:
        if s["id"] in {"ls2007", "reading_framework_2023"}:
            assert s["licence"] == "Open Government Licence v3.0"
            assert "Open Government Licence v3.0" in s["attribution"]
            assert s["url"].startswith("https://assets.publishing.service.gov.uk/")


def test_sources_toml_records_the_crown_copyright(corpus):
    for s in corpus.sources["source"]:
        if s["id"] == "ls2007":
            assert s["copyright"] == "© Crown copyright 2007"
            assert s["reference"] == "DFES-00281-2007"


def test_sources_toml_records_page_numbers(corpus):
    ls = next(s for s in corpus.sources["source"] if s["id"] == "ls2007")
    assert len(ls["pages_used"]) >= 20
    assert any("p.69" in p for p in ls["pages_used"])
    assert any("p.102" in p for p in ls["pages_used"])


def test_sources_toml_records_what_we_left_out(corpus):
    omitted = {o["word"] for o in corpus.sources["omitted"]}
    assert omitted == {"ass", "god", "queue", "whistle", "scene"}
    for o in corpus.sources["omitted"]:
        assert o["reason"]
    texts = {w.text for w in corpus.words}
    assert not (omitted & texts)


def test_data_files_carry_the_ogl_notice():
    from sounds_and_words.corpus import data_dir

    for name in ("graphemes.toml", "words.toml", "tricky_words.toml",
                 "sentences.toml", "lexicon.toml"):
        head = (data_dir() / name).read_text()[:400]
        assert "Open Government Licence v3.0" in head, name
        assert "Crown copyright" in head, name


# ------------------------------------------------------------ lowercase rule
def test_everything_child_facing_is_lowercase(corpus):
    for w in corpus.words:
        assert w.text == w.text.lower()
    for g in corpus.gpcs:
        assert g.grapheme == g.grapheme.lower()
    for t in corpus.tricky_words:
        assert t.text == t.text.lower()


def test_sentences_keep_the_printed_form_and_a_lowercase_form(corpus):
    for s in corpus.sentences:
        assert s.text_lower == s.text.lower()
    for t in corpus.texts:
        assert len(t.lines) == len(t.lines_lower)


# ------------------------------------------------------- internal consistency
def test_every_word_segmentation_uses_known_gpcs(corpus):
    known = set(corpus.gpc_by_id) | set(corpus.untaught_by_id)
    for w in corpus.words:
        for g in w.graphemes:
            assert g in known, f"{w.text}: {g}"


def test_every_lexicon_entry_uses_known_gpcs(corpus):
    known = set(corpus.gpc_by_id) | set(corpus.untaught_by_id)
    for e in corpus.lexicon:
        for g in e.graphemes:
            assert g in known, f"{e.word}: {g}"


def test_every_tricky_word_segmentation_uses_known_gpcs(corpus):
    known = set(corpus.gpc_by_id) | set(corpus.untaught_by_id)
    for t in corpus.tricky_words:
        for g in t.graphemes:
            assert g in known, f"{t.text}: {g}"


def test_word_order_equals_the_max_order_of_its_gpcs(corpus):
    by_id = corpus.gpc_by_id
    for w in corpus.words:
        if any(g not in by_id for g in w.graphemes):
            continue
        assert w.order == max(by_id[g].order for g in w.graphemes), w.text


def test_the_letters_spell_the_word(corpus):
    """The concatenated graphemes must reconstruct the word.

    Split digraphs and the never-taught pseudo-GPCs are exempt: one is
    discontinuous by definition, the other stands for nothing.
    """
    by_id = corpus.gpc_by_id
    exempt = set(corpus.untaught_by_id)
    for w in corpus.words:
        if any(g in exempt for g in w.graphemes):
            continue
        if any(by_id[g].split for g in w.graphemes):
            continue
        spelled = "".join(by_id[g].grapheme for g in w.graphemes)
        assert spelled == w.text.replace("-", "").replace("'", ""), w.text


def test_no_duplicate_words(corpus):
    texts = [w.text for w in corpus.words]
    assert len(texts) == len(set(texts))


def test_lexicon_does_not_shadow_the_word_banks(corpus):
    bank = {w.text for w in corpus.words}
    assert not (bank & {e.word for e in corpus.lexicon})


def test_every_sentence_token_has_a_segmentation(corpus):
    known = set(corpus.segmentations) | set(corpus.tricky_by_text)
    for s in corpus.sentences:
        for tok in s.tokens:
            assert tok in known, f"{tok!r} in {s.text!r}"


def test_every_text_token_has_a_segmentation(corpus):
    known = set(corpus.segmentations) | set(corpus.tricky_by_text)
    for t in corpus.texts:
        for tok in t.tokens:
            assert tok in known, f"{tok!r} in {t.title!r}"


def test_sentence_tokens_match_the_text(corpus):
    for s in corpus.sentences:
        assert list(s.tokens) == tokenise(s.text)


def test_never_taught_pseudo_gpcs_are_never_in_the_gpc_table(corpus):
    assert not (set(corpus.untaught_by_id) & set(corpus.gpc_by_id))
    for u in corpus.untaught:
        assert u.taught is False


def test_untaught_gpcs_are_actually_used(corpus):
    """A pseudo-GPC nobody references is dead weight, and probably a typo."""
    used = set()
    for seq in list(corpus.segmentations.values()) + [t.graphemes for t in corpus.tricky_words]:
        used.update(seq)
    unused = set(corpus.untaught_by_id) - used
    assert unused == set(), f"unused pseudo-GPCs: {sorted(unused)}"


# --------------------------------------------------------------- spoken labels
def test_no_spoken_label_is_a_schwa_spelling(corpus):
    """'suh' instead of 'sss' is the classic phonics error and we must not ship it."""
    bad = {"suh", "tuh", "puh", "buh", "duh", "kuh", "guh", "muh", "nuh", "fuh", "luh", "ruh"}
    for g in corpus.gpcs:
        assert g.spoken_label.lower() not in bad, g.id


def test_continuants_are_marked_stretchable(corpus):
    by_id = corpus.gpc_by_id
    for gid in ("s", "m", "n", "f", "l", "r", "sh", "th", "ng", "ee", "oo_long"):
        assert by_id[gid].stretchable, gid
    for gid in ("t", "p", "d", "k", "b", "g", "ch", "j"):
        assert not by_id[gid].stretchable, gid


def test_every_gpc_has_an_ipa_symbol_and_a_spoken_label(corpus):
    for g in corpus.gpcs:
        assert g.ipa
        assert g.spoken_label
        assert g.example_words


# --------------------------------------------------------------- segmentation
def test_order_of_last_grapheme_resolves_a_bare_grapheme(corpus):
    assert corpus.order_of_last_grapheme("ck") == corpus.gpc_by_id["ck"].order
    assert corpus.order_of_last_grapheme("ai") == corpus.gpc_by_id["ai"].order


def test_order_of_last_grapheme_prefers_the_first_teaching(corpus):
    """'oo' is taught once as /oo/ long and once short; the parent means the first."""
    assert corpus.order_of_last_grapheme("oo") == corpus.gpc_by_id["oo_long"].order
    assert corpus.order_of_last_grapheme("a") == corpus.gpc_by_id["a"].order


def test_order_of_last_grapheme_accepts_a_gpc_id(corpus):
    assert corpus.order_of_last_grapheme("oo_short") == corpus.gpc_by_id["oo_short"].order


def test_order_of_last_grapheme_rejects_nonsense(corpus):
    with pytest.raises(KeyError):
        corpus.order_of_last_grapheme("zq")


def test_segment_prefers_the_longest_grapheme():
    assert segment("night", {"n", "i", "g", "h", "t", "igh"}) == ("n", "igh", "t")
    assert segment("night", {"n", "i", "g", "h", "t"}) == ("n", "i", "g", "h", "t")


def test_segment_handles_trigraphs():
    assert segment("hear", {"h", "e", "a", "r", "ear"}) == ("h", "ear")


def test_segment_handles_doubled_consonants():
    assert segment("bell", {"b", "e", "l", "ll"}) == ("b", "e", "ll")


def test_segment_returns_none_when_it_cannot_finish():
    assert segment("zip", {"z", "i"}) is None


def test_segment_skips_split_digraphs():
    assert segment("make", {"m", "k", "a-e"}) is None


def test_tokenise_drops_punctuation():
    assert tokenise("Splash! Alex got wet.") == ["splash", "alex", "got", "wet"]
    assert tokenise("Let's run and see it.") == ["let's", "run", "and", "see", "it"]
    assert tokenise("ping-pong") == ["ping-pong"]
