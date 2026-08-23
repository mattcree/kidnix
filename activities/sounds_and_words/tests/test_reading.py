"""Read it: twelve books, and the one rule none of them may break.

The rule is the design constitution's (research 05 section 2a): *never show a
child a word containing a GPC they may not have been taught*. A connected text
is where that rule is easiest to break by accident, because a sentence is
written by a person reaching for the word they want, and the word they want is
usually one letter past the ceiling.

So the first section of this file walks **every word of every text, title
included, at the ceiling the text declares and at the one below it**, in strict
mode -- which refuses a word it has no segmentation for rather than guessing at
one. If the twelve texts and the corpus ever disagree, this is where it shows.

The rest is the screen's arithmetic, kept here because it is provable without a
display: how a book paginates, when each word lights up, which five books are
on a shelf page, and what the Journal card says.
"""

from __future__ import annotations

import json
from datetime import date
from itertools import pairwise

import pytest

from sounds_and_words.ceiling import (
    ceiling_for_grapheme,
    ceiling_from_order,
    check_lines,
    check_word,
    tokenise,
)
from sounds_and_words.reading import (
    MAX_LINES,
    MIN_LINES,
    SHELF_PER_PAGE,
    ReadingText,
    illustration_for,
    load_texts,
    missing_illustrations,
    rate_factor,
    sentence_ms,
    shelf_pages,
    span_at,
    text_by_slug,
    texts_for,
    word_spans,
)
from sounds_and_words.summary import (
    ReadingSummary,
    read_caption_for,
    read_meta_for,
)

#: How many there are. Research 10 section 7.1's week 4 asks for "~12 authored
#: decodable texts across Phases 2-3", and a number in a test is how that stops
#: being an aspiration.
EXPECTED = 12


@pytest.fixture(scope="module")
def texts():
    return load_texts()


def ids(texts):
    return [text.slug for text in texts]


# --- the twelve -------------------------------------------------------------


def test_there_are_twelve_of_them(texts):
    assert len(texts) == EXPECTED


def test_every_slug_is_distinct(texts):
    assert len(set(ids(texts))) == len(texts)


def test_every_title_is_distinct(texts):
    assert len({text.title for text in texts}) == len(texts)


def test_they_span_phase_two_sets_two_to_five(texts):
    """Not "Phase 2" as one lump: a child three weeks into Reception has set 2,
    and a book that needed set 5 would be no book at all to them."""
    sets = {text.set for text in texts if text.phase == 2}
    assert sets == {2, 3, 4, 5}


def test_they_span_phase_three_as_well(texts):
    assert any(text.phase == 3 for text in texts)


def test_phase_three_is_covered_at_more_than_one_point(texts):
    """Phase 3 is twenty-seven GPCs against Phase 2's twenty-three. One text
    for the whole of it would be one book for a term."""
    orders = {text.after_order for text in texts if text.phase == 3}
    assert len(orders) >= 4


def test_the_shelf_is_in_teaching_order(texts):
    orders = [text.after_order for text in texts]
    assert orders == sorted(orders)


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_every_text_is_four_to_eight_sentences(text):
    """Research 10 section 4.1 E. Four is short enough to finish; eight is
    where a five-year-old reading every word aloud runs out of session."""
    assert MIN_LINES <= len(text) <= MAX_LINES


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_every_line_has_a_drawing(text):
    assert len(text.pictures) == len(text.lines)


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_a_text_is_readable_at_the_order_it_claims(corpus, text):
    """Strict mode: a word with no segmentation on record is refused, not
    guessed at. Guessing is how an untaught GPC reaches a child."""
    ceiling = ceiling_from_order(corpus, text.after_order)
    verdict = check_lines(corpus, text.all_lines, ceiling, strict=True)
    assert verdict.allowed, verdict.report()


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_a_text_is_not_readable_one_order_earlier(corpus, text):
    """`after_order` is declared rather than computed so that a careless edit
    fails a test instead of quietly moving a book up a set. This is the half
    that catches a number set too high; the test above catches one set too
    low."""
    below = ceiling_from_order(corpus, text.after_order - 1)
    assert not check_lines(corpus, text.all_lines, below, strict=True).allowed


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_the_title_is_held_to_the_same_rule_as_a_sentence(corpus, text):
    """A child reads the title off the shelf. It is not chrome."""
    ceiling = ceiling_from_order(corpus, text.after_order)
    for token in tokenise(text.title):
        assert check_word(corpus, token, ceiling).allowed, (text.slug, token)


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_no_digit_appears_anywhere_in_a_text(text):
    """01 #19: no digits where a child can see them. "ten hens" is a word."""
    for line in (text.title, *text.lines):
        assert not any(character.isdigit() for character in line), line


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_everything_is_lowercase(text):
    """Design note section 2.2: everything child-facing here is lowercase, and
    the L&S caption bank these words come from is set that way too."""
    for line in (text.title, *text.lines):
        assert line == line.lower(), line


@pytest.mark.parametrize("text", load_texts(), ids=lambda t: t.slug)
def test_every_line_ends_in_a_stop_of_some_kind(text):
    assert all(line.rstrip()[-1] in ".!?" for line in text.lines)


def test_no_word_in_any_text_needs_a_gpc_past_phase_three(corpus, texts):
    """The whole set is Phases 2-3, which is what week 4 asked for. A Phase 5
    grapheme in one of them would be readable by nobody this activity ships
    for."""
    phase3 = ceiling_from_order(corpus, max(text.after_order for text in texts))
    for text in texts:
        assert check_lines(corpus, text.all_lines, phase3, strict=True).allowed, text.slug


def test_a_text_that_reached_past_its_ceiling_would_be_caught(corpus):
    """A test that cannot fail is not a test."""
    made_up = ReadingText(
        slug="x",
        title="a cat",
        phase=2,
        after_order=8,
        lines=("a cat sat.",),
        pictures=("cat",),
        cover="cat",
    )
    assert not check_lines(corpus, made_up.all_lines, ceiling_from_order(corpus, 8)).allowed


def test_lines_and_pictures_must_agree_in_number():
    with pytest.raises(ValueError):
        ReadingText(
            slug="x",
            title="a cat",
            phase=2,
            after_order=11,
            lines=("a cat sat.", "a cat sat."),
            pictures=("cat",),
            cover="cat",
        )


def test_the_words_of_a_book_are_distinct_and_in_order(texts):
    book = text_by_slug("a-cat-and-a-dog", texts=texts)
    assert book is not None
    assert book.words[:4] == ("a", "cat", "sits", "on")
    assert len(book.words) == len(set(book.words))


def test_an_unknown_slug_is_none(texts):
    assert text_by_slug("no-such-book", texts=texts) is None


# --- the drawings -----------------------------------------------------------


def test_every_drawing_a_text_names_is_really_on_disk():
    """A picture named in data and missing on disk is an empty frame beside a
    sentence, and an empty frame is worse than no frame."""
    assert missing_illustrations() == []


def test_the_fifteen_nouns_are_reused_rather_than_redrawn(texts):
    """The scenes are the ones no single-noun drawing covers. A second cat
    would be a second cat to keep in step with the first."""
    from sounds_and_words.pictures import PICTURE_WORDS

    used = {name for text in texts for name in (text.cover, *text.pictures)}
    assert used & set(PICTURE_WORDS), "no noun drawing is reused at all"


def test_a_drawing_that_is_not_there_is_none_rather_than_a_broken_path():
    assert illustration_for("no-such-drawing") is None
    assert illustration_for("") is None


def test_a_scene_wins_over_a_noun_of_the_same_name(tmp_path):
    scenes = tmp_path / "scenes"
    pictures = tmp_path / "pictures"
    scenes.mkdir()
    pictures.mkdir()
    (scenes / "cat.svg").write_text("<svg/>")
    (pictures / "cat.svg").write_text("<svg/>")
    assert illustration_for("cat", scenes=scenes, pictures=pictures) == scenes / "cat.svg"


# --- pagination -------------------------------------------------------------


@pytest.fixture(scope="module")
def book(texts):
    found = text_by_slug("ducks-at-the-pond", texts=texts)
    assert found is not None
    return found


def test_one_sentence_is_one_page(book):
    assert len(book.pages) == len(book.lines)
    assert [page.sentence for page in book.pages] == list(book.lines)


def test_every_page_knows_where_it_is(book):
    pages = book.pages
    assert pages[0].first and not pages[0].last
    assert pages[-1].last and not pages[-1].first
    assert all(page.total == len(book) for page in pages)


def test_a_page_carries_its_own_drawing(book):
    assert [page.picture for page in book.pages] == list(book.pictures)


def test_asking_for_a_page_that_is_not_there_gives_nothing(book):
    assert book.page(len(book)) is None
    assert book.page(-1) is None
    assert book.page(0) == book.pages[0]


def test_a_pages_words_are_the_written_ones_punctuation_and_all(texts):
    """What gets highlighted is what is on the glass, and on the glass "tap,"
    is one word with a comma on it. The tokeniser's answer is a different
    question about the same sentence."""
    pot = text_by_slug("tap-a-tin-pot", texts=texts)
    page = pot.pages[2]
    assert page.words == ("tap,", "tap,", "tap!")
    assert tokenise(page.sentence) == ["tap", "tap", "tap"]


# --- the highlight ----------------------------------------------------------


def test_a_span_for_every_written_word():
    spans = word_spans("a cat sits on a mat.")
    assert len(spans) == 6
    assert [span.word for span in spans][:2] == ["a", "cat"]


def test_the_spans_start_at_zero_and_are_gapless():
    spans = word_spans("the ducks get in the pond.")
    assert spans[0].start_ms == 0
    for before, after in pairwise(spans):
        assert before.end_ms == after.start_ms


def test_the_last_span_ends_exactly_on_the_total():
    total = 4000
    spans = word_spans("the ducks get in the pond.", total_ms=total)
    assert spans[-1].end_ms == total


def test_a_longer_word_is_lit_for_longer():
    """Equal shares would give "a" the same beat as "farmyard", which is
    visibly wrong on any line with a one-letter word in it."""
    spans = {span.word: span.duration_ms for span in word_spans("a farmyard.")}
    assert spans["farmyard."] > spans["a"]


def test_every_span_lasts_at_least_a_moment():
    spans = word_spans("a a a a a a a a a a", total_ms=3)
    assert all(span.duration_ms >= 1 for span in spans)


def test_an_empty_line_has_no_spans():
    assert word_spans("") == ()
    assert word_spans("   ") == ()
    assert sentence_ms("") == 0


def test_a_slower_voice_gets_a_slower_highlight():
    """`[access] speech_rate` is the parent's, and calm mode arrives through
    the same number. A highlight that ignored it would run away from the
    voice."""
    slow = sentence_ms("the ducks get in the pond.", rate=-80)
    normal = sentence_ms("the ducks get in the pond.", rate=0)
    fast = sentence_ms("the ducks get in the pond.", rate=80)
    assert slow > normal > fast


def test_the_rate_factor_is_clamped_at_both_ends():
    assert rate_factor(-100) == pytest.approx(1.5)
    assert rate_factor(0) == pytest.approx(1.0)
    assert rate_factor(1000) == rate_factor(100)
    assert rate_factor(-1000) == rate_factor(-100)


def test_a_longer_sentence_takes_longer_to_say():
    assert sentence_ms("a cat.") < sentence_ms("a cat sat on a mat in the sun.")


def test_the_word_lit_at_a_moment_is_the_one_whose_span_contains_it():
    spans = word_spans("a cat sat.", total_ms=3000)
    assert span_at(spans, 0) is spans[0]
    assert span_at(spans, spans[1].start_ms) is spans[1]
    assert span_at(spans, 3000) is None


def test_nothing_is_lit_before_the_line_starts():
    spans = word_spans("a cat sat.", total_ms=3000)
    assert span_at(spans, -1) is None


def test_the_spans_cover_the_whole_line_and_no_more():
    spans = word_spans("gran gets the hens back in the pen.", total_ms=5000)
    assert sum(span.duration_ms for span in spans) == 5000


# --- the shelf --------------------------------------------------------------


def test_a_tiny_ceiling_admits_no_book_at_all(corpus):
    assert texts_for(corpus, ceiling_from_order(corpus, 0)) == []
    assert texts_for(corpus, ceiling_for_grapheme(corpus, "t")) == []


def test_set_two_admits_exactly_the_set_two_book(corpus):
    admitted = texts_for(corpus, ceiling_for_grapheme(corpus, "d"))
    assert ids(admitted) == ["sam-and-sid"]


def test_the_shelf_grows_as_the_school_teaches_more(corpus):
    sizes = [
        len(texts_for(corpus, ceiling_for_grapheme(corpus, grapheme)))
        for grapheme in ("d", "k", "r", "ss", "er")
    ]
    assert sizes == sorted(sizes)
    assert sizes[-1] == EXPECTED


def test_every_book_on_a_shelf_is_decodable_at_that_ceiling(corpus):
    """The gate is applied to the whole text rather than to its declared
    order: a mistyped number in the TOML must not be able to put a book on a
    shelf."""
    for grapheme in ("d", "k", "r", "ss", "th", "er"):
        ceiling = ceiling_for_grapheme(corpus, grapheme)
        for book in texts_for(corpus, ceiling):
            assert check_lines(corpus, book.all_lines, ceiling, strict=True).allowed


def test_no_shelf_page_holds_more_than_five(corpus):
    """ADR-0013: five is the bound on a choice the child has to weigh, and a
    shelf of books is squarely a choice."""
    books = texts_for(corpus, ceiling_for_grapheme(corpus, "er"))
    pages = shelf_pages(books)
    assert all(len(page) <= SHELF_PER_PAGE for page in pages)
    assert sum(len(page) for page in pages) == len(books)


def test_the_twelve_come_out_as_three_pages(corpus):
    books = texts_for(corpus, ceiling_for_grapheme(corpus, "er"))
    assert [len(page) for page in shelf_pages(books)] == [5, 5, 2]


def test_a_caller_asking_for_a_bigger_page_is_capped_not_refused(corpus):
    """Refusing would turn a design mistake into a child staring at a screen
    that will not start."""
    books = texts_for(corpus, ceiling_for_grapheme(corpus, "er"))
    assert all(len(page) <= SHELF_PER_PAGE for page in shelf_pages(books, per_page=9))


def test_a_page_size_of_zero_is_one_rather_than_a_division_by_nothing(corpus):
    books = texts_for(corpus, ceiling_for_grapheme(corpus, "d"))
    assert shelf_pages(books, per_page=0) == ((books[0],),)


def test_an_empty_shelf_has_no_pages():
    assert shelf_pages([]) == ()


def test_the_shelf_never_shows_a_book_from_next_term(corpus):
    """The one that matters. Walk every ceiling this corpus can express and
    assert nothing above it ever appears."""
    for order in range(0, corpus.max_order() + 1):
        ceiling = ceiling_from_order(corpus, order)
        for book in texts_for(corpus, ceiling):
            assert book.after_order <= order, (order, book.slug)


# --- the Journal card -------------------------------------------------------


def test_the_caption_says_what_happened_in_the_childs_own_voice():
    assert read_caption_for("a trip to nan") == "I read: a trip to nan"


def test_the_caption_counts_nothing():
    caption = read_caption_for("in the farmyard")
    assert not any(character.isdigit() for character in caption)
    for forbidden in ("well done", "score", "star", "level", "streak"):
        assert forbidden not in caption.lower()


def test_the_caption_survives_a_title_with_spaces_round_it():
    assert read_caption_for("  ten hens  ") == "I read: ten hens"


def test_the_meta_carries_the_phase_and_the_words(texts):
    book = text_by_slug("ten-hens", texts=texts)
    meta = read_meta_for(
        book.title,
        slug=book.slug,
        phase=book.phase,
        words=book.words,
        day=date(2026, 8, 23),
        ceiling_label="up to 'ss'",
    )
    assert meta["phase"] == 2
    assert meta["title"] == "ten hens"
    assert "hens" in meta["words"]
    assert meta["date"] == "2026-08-23"
    assert meta["ceiling"] == "up to 'ss'"


def test_the_meta_is_json_serialisable_before_anything_is_copied(texts):
    book = text_by_slug("ten-hens", texts=texts)
    meta = ReadingSummary(title=book.title, slug=book.slug, phase=2, words=book.words).meta
    assert json.loads(json.dumps(meta))["slug"] == "ten-hens"


def test_the_meta_holds_no_score_of_any_kind(texts):
    book = text_by_slug("ten-hens", texts=texts)
    meta = ReadingSummary(title=book.title, slug=book.slug, phase=2, words=book.words).meta
    assert set(meta) == {"title", "slug", "phase", "words", "date", "ceiling"}


def test_the_summary_reads_its_caption_from_its_title():
    assert ReadingSummary(title="a big box").caption == "I read: a big box"


# --- the drawing of the card ------------------------------------------------

gi = pytest.importorskip("gi", reason="no PyGObject: the card cannot be drawn")


def test_a_reading_card_is_written_and_is_a_real_png(tmp_path, texts):
    book = text_by_slug("a-trip-to-nan", texts=texts)
    summary = ReadingSummary(title=book.title, slug=book.slug, phase=book.phase, words=book.words)
    path = summary.write(tmp_path / "read.png")
    assert path.is_file()
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert path.stat().st_size > 1000


def test_the_card_directory_is_created(tmp_path):
    path = ReadingSummary(title="ten hens").write(tmp_path / "deep" / "read.png")
    assert path.is_file()


def test_a_card_for_the_longest_title_still_renders(tmp_path, texts):
    longest = max(texts, key=lambda text: len(text.title))
    assert ReadingSummary(title=longest.title).write(tmp_path / "long.png").is_file()
