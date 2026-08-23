"""Running Letters and Sounds back through its own gate.

Transcribing the banks and then filtering them at the phase they are printed in
turns up a short list of places where the document does not meet its own
standard. These are not transcription errors: they are in the PDF. kidnix's
filter rejects those sentences at those phases, which is the correct behaviour
and the whole point of having a filter.

The list is pinned here so that it cannot drift silently. If a change to the
corpus or the ceiling makes it longer, something has broken; if it makes it
shorter, something has been quietly over-permitted, which is worse.
"""

from __future__ import annotations

from sounds_and_words.ceiling import ceiling_from_order, check_lines, check_text

# (text, the words that block it at its own printed phase)
KNOWN_SENTENCE_EXCEPTIONS = {
    # p.71: printed under "Captions with sets 1-3 words", but 'h' is a set 5 letter.
    "a cat in a hat": {"hat"},
    # p.101: 'into' -- the final 'o' stands for /oo/, a Phase Five alternative.
    "We can get the big bed into the van.": {"into"},
    # p.101: printed with the four consonant digraphs, but 'are' is not taught
    # until week 10 of Phase Three.
    "A moth can be fat, but its wings are thin.": {"are"},
    # p.128: 'into' again.
    "I kept bumping into things in the dark.": {"into"},
    "A crab crept into a crack in the rock.": {"into"},
    # p.128: 'by' -- 'y' standing for /igh/ is Phase Five.
    "Have you seen a trail left by a snail?": {"by"},
}

KNOWN_TEXT_EXCEPTIONS = {
    "on the farm": {"into"},
    "in town": {"may"},          # 'ay' is a Phase Five grapheme
}


def test_the_exception_list_is_exactly_this_long(corpus):
    failing = {}
    for s in corpus.sentences:
        c = ceiling_from_order(corpus, s.after_order, phase=s.phase)
        v = check_text(corpus, s.text, c)
        if not v.allowed:
            failing[s.text] = set(v.blocked_words)
    assert failing == KNOWN_SENTENCE_EXCEPTIONS


def test_the_text_exception_list_is_exactly_this_long(corpus):
    failing = {}
    for t in corpus.texts:
        c = ceiling_from_order(corpus, t.after_order, phase=t.phase)
        v = check_lines(corpus, t.lines, c)
        if not v.allowed:
            failing[t.title] = set(v.blocked_words)
    assert failing == KNOWN_TEXT_EXCEPTIONS


def test_the_overwhelming_majority_of_the_banks_pass_their_own_gate(corpus):
    ok = sum(
        1 for s in corpus.sentences
        if check_text(corpus, s.text, ceiling_from_order(corpus, s.after_order, phase=s.phase)).allowed
    )
    assert ok / len(corpus.sentences) > 0.94


def test_every_word_bank_entry_is_decodable_at_its_own_order(corpus):
    """The stronger claim, and the one that matters: every *word* we ship is
    decodable exactly at the order we tagged it with, and not before."""
    for w in corpus.words:
        at = ceiling_from_order(corpus, w.order, phase=w.phase)
        assert set(w.graphemes) <= at.gpc_ids, w.text
        if w.order > 1:
            before = ceiling_from_order(corpus, w.order - 1)
            assert not set(w.graphemes) <= before.gpc_ids, w.text


def test_words_printed_in_a_column_they_outrun_are_flagged(corpus):
    """L&S prints 'Ken' under set 3, though the 'e' it needs is a set 4 letter.

    Those words are kept -- they are in the document -- but they carry
    `order_exceeds_group` and gate on their true order.
    """
    flagged = [w for w in corpus.words if w.order_exceeds_group]
    assert flagged
    assert all(w.note for w in flagged)
    ken = corpus.word_by_text["ken"]
    assert ken.order_exceeds_group
    assert ken.order == corpus.gpc_by_id["e"].order


def test_the_audit_is_recorded_in_sources_toml(corpus):
    findings = corpus.sources["audit"]
    assert len(findings) >= 2
    joined = " ".join(f["detail"] for f in findings)
    for word in ("into", "may", "by", "Ken"):
        assert word in joined
    assert "test_letters_and_sounds_audit.py" in joined
