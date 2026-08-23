# ADR-0012: Internationalisation — GNU gettext, per-profile language, en_GB as the source

**Status:** accepted, 2026-08-23
**Supersedes/amends:** nothing. Extends ADR-0004 (GTK4/Python shell) and
ADR-0008 (speech-dispatcher + espeak/Piper).
**Evidence:** `docs/research/06 §4.7`, `§4.1`; `docs/spikes/tts.md §1`.
**Detail:** `docs/design/i18n.md`.

## Context

kidnix is a **UK** children's OS, and the UK a five-year-old actually lives in
is not monolingual:

- **23.8% of pupils in English primary schools have a first language other than
  English** (DfE, January 2026 census); 30.6% in nurseries. That is not a
  minority use case, it is a quarter of the target population.
- **Polish is the largest** of those languages in England and Wales — 612,000
  speakers (Census 2021) — followed by Romanian, Panjabi and Urdu. Local
  concentration is extreme: Slough is 4.3% Urdu, Boston 5.7% Polish.
- **Welsh fell 6.0 percentage points among 5–15 year olds** between the 2011
  and 2021 censuses — kidnix's exact age group. A Welsh mode is the one place
  where this project could make a measurable contribution rather than just
  being usable.

Against that, v0.1 hard-codes about 240 English sentences in Python source,
several of them assembled with f-strings (`f"{name} things"`,
`f"Ready to {phrase}?"`), and sends a hard-coded `en-GB` to
speech-dispatcher. None of that is a translation problem yet; it is a
*structural* one, and every week it costs more to fix.

The forcing question was not "shall we ship Welsh" — we cannot, responsibly,
without a Welsh speaker who teaches five-year-olds. It was "is the shell
*shaped* so that shipping Welsh is a translation job rather than a rewrite".

## Decision

**1. GNU gettext, one domain (`kidnix`), msgids in en_GB.**
No framework, no lazy-string proxy, no per-language Python modules. The
en_GB strings *are* the message ids, so a machine with no catalogue installed
returns them unchanged and behaves **byte-identically** to the shell before
this ADR. That property is asserted, not assumed
(`tests/test_i18n.py::test_english_is_byte_identical_with_the_catalogues_available`,
and again inside the image in `tests/image/test_shell.sh`).

**2. Two marking functions, and the difference is when.**
`_()` translates *now* — inside a method, where "now" is when the sentence is
shown. `N_()` / `NP_()` mark a module-level constant for extraction and
translate *later*, at the use site. The rule is absolute: **never `_()` at
module level**, because a module-level `_()` freezes whatever language happened
to be installed when Python first imported the file. This is the deferred
translation idiom from the Python `gettext` docs, and it is what let every
existing constant (`RESTING_TITLE`, `OFFER_QUESTION`, `LOTS_LEFT`) keep its
name, its value and its tests.

**3. Plurals go through `ngettext`, always.** Welsh has **six** plural forms
and Polish three; "singular or plural" is an English answer to a question
English happens to make easy. Every counted noun in the shell — the Goodbye
sentence, the grown-up sheet's minutes — asks the catalogue's own
`Plural-Forms` rule. Numbers 0–20 are words from `kidnix_shell/words.py`,
translated, because the child never sees a digit (01 #19).

**4. Language comes from the profile first.** In order: the active profile's
`language`, then `[access] language` in `parent.toml`, then the environment,
then `en_GB`. Per-*child* and not per-machine because a bilingual household is
one where the siblings differ — and because research 06 §4.7's own reading is
that "parents' and children's language needs differ".

**5. A profile switch rebuilds the screens.** A GTK label is a string that was
built once, so changing the catalogue does not change what is already on
screen. When — and only when — the incoming profile's language differs from
the one in force, the shell reinstalls the catalogue, sends the new language to
speech-dispatcher, and rebuilds its surfaces on the next main-loop turn
(`ShellWindow._use_language`). `_build_content()` already existed for monitor
changes and screens own no state that outlives them, so this is four lines. A
same-language switch — every switch on a monolingual machine — does nothing at
all, which is why the en_GB path is untouched.

**6. Read-aloud follows the text.** The shell sends SSIP `SET SELF LANGUAGE`
with its own locale. A Welsh Home screen read aloud in an English voice is
*worse* than either alone, because a child learning to match a shape to a word
hears the letters mispronounced. Only `en_GB-cori` (Piper) is bundled; every
other language falls through to espeak-ng, which is intelligible and not
beautiful. Captions are the text that was spoken and need nothing.

**7. Activity manifests carry their own translations.** `name_cy`,
`audio_label_pl` beside `name` and `audio_label`, resolved most-specific-first
by `kidnix_shell.activities.localised`. A manifest is content from a package we
did not write; it does not belong in our catalogue.

**8. Two sample catalogues, and they are labelled as samples.**
`shell/po/cy.po` and `shell/po/pl.po` carry ~20 well-known words each and a
correct `Plural-Forms` header, and say in their own comments that they are a
pipeline demonstration and not a reviewed translation. They exist to prove six
plural forms and three survive the round trip, and that a half-translated
catalogue degrades to en_GB **per string**.

**9. What is not localised, by design.** Activity *corpora*. Sounds & Words is
English phonics; a Welsh child needs Welsh phonics, which is a different
activity with different content and a different pedagogy, not a translated
string table. Saying so is the honest position and is recorded in
`docs/design/i18n.md §6`.

**10. RTL is out of scope for v0.1.** Urdu and Arabic need mirrored layout,
Nastaliq shaping and a font Andika does not cover. Recording that we know is
better than a half-mirrored Home screen.

## Alternatives rejected

**A lazy string proxy** (Django's `gettext_lazy`). It would have removed rule 2
and the `N_()` ceremony. Rejected because a `str`-like object that is not a
`str` leaks into `.format()`, `f"{...}"`, `frozenset` membership, `==` in 60
existing tests and PyGObject's C boundary, and every one of those failures
appears at runtime, in front of a child, in a language nobody on this project
reads.

**Rebuilding nothing on a profile switch** (set the voice, log a note, apply
text at next start). Cheaper, and it is what the brief allowed. Rejected
because `_build_content()` already exists and is already called for a monitor
change: the honest cost was four lines, and "your sibling's language until you
reboot" is a bad answer to give a second child.

**pybabel** for extraction. Rejected: `xgettext`/`msgfmt` are two C programs
that do the job in 40 ms and are already in the image; a Python build-time
dependency for that is a dependency.

**Committing the compiled `.mo`.** Rejected: a repository carrying both `.po`
and `.mo` has two sources of truth and no way to notice when they disagree.
`build_files/60-shell.sh` compiles from the `.po` at image build, and `just
po-compile` does the same for a dev checkout.

## Consequences

- ~240 msgids; `shell/po/kidnix.pot` is generated and reviewable.
- A pytest AST guard (`test_no_child_facing_string_escapes_gettext`) fails the
  build if a new sentence in `band.py`, `ritual.py`, `resting.py`,
  `feedback.py`, `suggestions.py`, `next_after.py`, `sun.py`, `words.py` or any
  `screens/*.py` is added outside `_()`/`N_()`/`NP_()`/`ngettext()`.
- `just po-extract`, `just po-update`, `just po-compile`, `just po-check`;
  `po-check` is in `just ci`.
- Adding a language is: one `.po`, one Piper voice (or espeak), a font check.
  It is not a code change. That was the point.
- **Open:** number-word agreement. `"{count} thing"` puts a *word* in
  `{count}`, and in Polish "one" inflects with its noun (*jedna* rzecz, not
  *jeden* rzecz). A translator can only fix this by folding the number into
  each plural form. Noted in `docs/design/i18n.md §2.3`; it needs a native
  speaker's judgement, not a mechanism.
