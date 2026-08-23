"""Regenerate the TOML corpus from the transcribed Letters and Sounds tables.

    uv run python tools/gen.py

`lsdata.py` is the transcription (page by page, column by column) and
`lexicon_data.py` is the hand-written grapheme-phoneme segmentation for words
that longest-match would get wrong. This script joins them, segments every
word, computes the order each word becomes decodable at, and writes `data/`.

It is the reason `data/*.toml` says "do not edit by hand": an edit there would
be silently reverted the next time anyone runs this.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import lsdata
from lexicon_data import LEXICON

OUT = Path(os.environ.get("SW_DATA_OUT")
           or Path(__file__).resolve().parent.parent / "data")

# Split-digraph words: longest match cannot see a discontinuous grapheme.
SPLIT_LEXICON = {
    "came": ["c", "a-e", "m"], "made": ["m", "a-e", "d"], "make": ["m", "a-e", "k"],
    "take": ["t", "a-e", "k"], "game": ["g", "a-e", "m"], "race": ["r", "a-e", "c_s"],
    "same": ["s", "a-e", "m"], "snake": ["s", "n", "a-e", "k"], "amaze": ["a", "m", "a-e", "z"],
    "escape": ["e", "s", "c", "a-e", "p"],
    "these": ["th_voiced", "e-e", "s_z"], "pete": ["p", "e-e", "t"], "eve": ["e-e", "v"],
    "steve": ["s", "t", "e-e", "v"], "even": ["e_ee", "v", "e", "n"],
    "theme": ["th", "e-e", "m"], "gene": ["g_j", "e-e", "n"],
    "scene": ["s", "silent", "e-e", "n"], "complete": ["c", "o", "m", "p", "l", "e-e", "t"],
    "extreme": ["e", "x", "t", "r", "e-e", "m"],
    "like": ["l", "i-e", "k"], "time": ["t", "i-e", "m"], "pine": ["p", "i-e", "n"],
    "ripe": ["r", "i-e", "p"], "shine": ["sh", "i-e", "n"], "slide": ["s", "l", "i-e", "d"],
    "prize": ["p", "r", "i-e", "z"], "nice": ["n", "i-e", "c_s"],
    "invite": ["i", "n", "v", "i-e", "t"], "inside": ["i", "n", "s", "i-e", "d"],
    "bone": ["b", "o-e", "n"], "pole": ["p", "o-e", "l"], "home": ["h", "o-e", "m"],
    "alone": ["a", "l", "o-e", "n"], "those": ["th_voiced", "o-e", "s_z"],
    "stone": ["s", "t", "o-e", "n"], "woke": ["w", "o-e", "k"], "note": ["n", "o-e", "t"],
    "explode": ["e", "x", "p", "l", "o-e", "d"],
    "envelope": ["e", "n", "v", "e", "l", "o-e", "p"],
    "june": ["j", "u-e_oo", "n"], "flute": ["f", "l", "u-e_oo", "t"],
    "prune": ["p", "r", "u-e_oo", "n"], "rude": ["r", "u-e_oo", "d"], "rule": ["r", "u-e_oo", "l"],
    "huge": ["h", "u-e_yoo", "g_j"], "cube": ["c", "u-e_yoo", "b"], "tube": ["t", "u-e_yoo", "b"],
    "use": ["u-e_yoo", "s_z"], "computer": ["c", "o", "m", "p", "u_yoo", "t", "er"],
    "white": ["wh", "i-e", "t"],
}

# L&S bank entries deliberately not shipped, with the reason.
OMITTED = [
    ("ass", "ls2007:p.70", "in the (+ss) column; not a word we want a five-year-old's "
                           "machine to offer unprompted"),
    ("god", "ls2007:p.69", "in the (+o) column; religious proper noun, out of scope for a "
                           "phonics word bank"),
    ("queue", "ls2007:p.151", "listed under 'ue' but not analysable as a decodable string"),
    ("whistle", "ls2007:p.151", "listed under 'wh' but needs the 'le' syllable, which L&S "
                                "never teaches as a GPC"),
    ("scene", "ls2007:p.152", "listed under 'e-e' but its 'c' stands for no phoneme at all, "
                              "so it can never pass any ceiling"),
    ("gail", "ls2007:p.102", "duplicate of the proper noun already carried; kept, see words.toml"),
]
OMITTED_WORDS = {"ass", "god", "queue", "whistle", "scene"}

PROPER_NOUNS = {
    "pam", "tim", "sam", "sid", "kim", "ken", "mog", "ben", "bill", "nell", "tess", "jill",
    "jack", "jen", "vic", "ravi", "kevin", "zak", "gail", "azam", "liz", "natasha", "sasha",
    "kath", "josh", "mark", "carl", "jim", "gurdeep", "nan", "alex", "jon", "jeevan", "max",
    "vikram", "jeff", "yasmin", "tanya", "yasha", "shep", "chip", "janaki", "zinat",
    "chester", "manchester", "grinch", "spain", "fred", "brett", "mars", "philip", "philippa",
    "christopher", "andrew", "matthew", "paul", "saul", "august", "roy", "floyd", "joe",
    "june", "pete", "eve", "steve", "sue", "prue", "welsh",
}


def build_gpcs() -> list[dict]:
    rows = []
    for (gid, graph, order, phase, sett, ipa, label, stretch, kind, ex, src, extra) in lsdata.GPCS:
        row = dict(id=gid, grapheme=graph, order=order, phase=phase, ipa=ipa,
                   spoken_label=label, stretchable=stretch, kind=kind,
                   example_words=ex, source=src)
        if sett is not None:
            row["set"] = sett
        row.update(extra)
        rows.append(row)
    base = {r["id"]: r for r in rows}
    for dbl, single, ex in lsdata.KIDNIX_DOUBLETS:
        s = base[single]
        rows.append(dict(
            id=dbl, grapheme=dbl, order=16, phase=2, set=4, ipa=s["ipa"],
            spoken_label=s["spoken_label"], stretchable=s["stretchable"], kind="doubled",
            example_words=ex, source="kidnix", added_by="kidnix", variant_of=single,
            note=("L&S never introduces this doubled consonant as a GPC, but uses it in its own "
                  "word banks from set 4 onward (rocket, carrot, rabbit). Added at order 16 so "
                  "those words segment into the right number of phonemes."),
        ))
    rows.sort(key=lambda r: (r["order"], r["id"]))
    return rows


GPCS = build_gpcs()
BY_ID = {g["id"]: g for g in GPCS}
UNTAUGHT_IDS = {u[0] for u in lsdata.UNTAUGHT}


def taught_at(order: int, prefer: dict[str, str] | None = None) -> dict[str, str]:
    """grapheme -> gpc id, for every GPC taught by `order`."""
    out: dict[str, str] = {}
    for g in GPCS:
        if g["order"] > order:
            continue
        gr = g["grapheme"]
        if gr not in out or BY_ID[out[gr]]["order"] > g["order"]:
            out[gr] = g["id"]
    if prefer:
        out.update(prefer)
    return out


def longest_match(word: str, table: dict[str, str]) -> list[str] | None:
    graphs = sorted(table, key=len, reverse=True)
    out: list[str] = []
    i = 0
    while i < len(word):
        for gr in graphs:
            if "-" in gr:
                continue  # split digraphs are discontinuous
            if word.startswith(gr, i):
                out.append(table[gr])
                i += len(gr)
                break
        else:
            return None
    return out


def order_of(gpcs: list[str]) -> int:
    return max((BY_ID[g]["order"] if g in BY_ID else 999) for g in gpcs)


def segment(word: str, after: int, prefer: dict[str, str] | None = None) -> list[str] | None:
    if word in LEXICON:
        return list(LEXICON[word][0])
    if word in SPLIT_LEXICON:
        return list(SPLIT_LEXICON[word])
    cleaned = word.replace("-", "").replace("'", "")
    return longest_match(cleaned, taught_at(after, prefer))


# ---------------------------------------------------------------- words.toml
def build_words() -> tuple[list[dict], list[str]]:
    words: list[dict] = []
    seen: dict[str, dict] = {}
    problems: list[str] = []
    for grp in lsdata.WORD_GROUPS:
        target = grp["target"]
        prefer = None
        if target and target in BY_ID:
            prefer = {BY_ID[target]["grapheme"]: target}
        for w in grp["words"]:
            if w in OMITTED_WORDS:
                continue
            gpcs = segment(w, grp["after"], prefer)
            if gpcs is None:
                problems.append(f"{w!r} in {grp['group']!r} did not segment")
                continue
            unknown = [g for g in gpcs if g not in BY_ID and g not in UNTAUGHT_IDS]
            if unknown:
                problems.append(f"{w!r} references unknown gpc ids {unknown}")
                continue
            order = order_of(gpcs)
            late = order > grp["after"]
            if w in seen:
                seen[w]["groups"].append(grp["group"])
                continue
            row = dict(
                text=w, phase=grp["phase"], order=order, graphemes=gpcs,
                groups=[grp["group"]], source=grp["source"],
            )
            if late:
                row["order_exceeds_group"] = True
                row["note"] = (
                    f"L&S prints this word in the {grp['group']!r} column, but decoding it "
                    f"needs a GPC not taught until order {order}. The order field, not the "
                    f"column, is what the ceiling gates on."
                )
            if grp["ls_set"] is not None:
                row["set"] = grp["ls_set"]
            if target:
                row["target_gpc"] = target
            if w in PROPER_NOUNS:
                row["proper_noun"] = True
            words.append(row)
            seen[w] = row
    hfw = {w for lst in lsdata.DECODABLE_HFW.values() for w in lst}
    for row in words:
        if row["text"] in hfw:
            row["high_frequency"] = True
    # decodable high-frequency words L&S names but that are not in a bank column
    for phase, lst in lsdata.DECODABLE_HFW.items():
        for w in lst:
            if w in seen:
                continue
            gpcs = segment(w, 50)
            if gpcs is None:
                problems.append(f"HFW {w!r} did not segment")
                continue
            row = dict(text=w, phase=phase, order=order_of(gpcs), graphemes=gpcs,
                       groups=["high-frequency words decodable by the end of this phase"],
                       source=f"ls2007: high-frequency words, phase {phase}",
                       high_frequency=True)
            words.append(row)
            seen[w] = row
    words.sort(key=lambda r: (r["order"], r["text"]))
    return words, problems


# ------------------------------------------------------------ TOML emission
def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(val(x) for x in v) + "]"
    return f'"{esc(str(v))}"'


def table(name: str, row: dict) -> str:
    lines = [f"[[{name}]]"]
    lines += [f"{k} = {val(v)}" for k, v in row.items()]
    return "\n".join(lines) + "\n"


HEADER = """# Generated from Letters and Sounds (2007), DFES-00281-2007.
# Contains public sector information licensed under the Open Government Licence v3.0.
# (c) Crown copyright 2007.
# See LICENSES.md and data/sources.toml. Do not edit by hand -- see the design doc.
"""


def tokenise(sentence: str) -> list[str]:
    return [t for t in re.findall(r"[a-z']+(?:-[a-z']+)*", sentence.lower()) if t.strip("'")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    words, problems = build_words()

    # ---- graphemes.toml
    out = [HEADER, '\nscheme = "letters_and_sounds"\nversion = 1\n']
    for g in GPCS:
        out.append("\n" + table("gpc", g))
    for uid, graph, desc, ex in lsdata.UNTAUGHT:
        out.append("\n" + table("untaught", dict(
            id=uid, grapheme=graph, description=desc, example_words=ex, taught=False)))
    (OUT / "graphemes.toml").write_text("".join(out))

    # ---- words.toml
    out = [HEADER, f"\nsource = \"ls2007\"\ncount = {len(words)}\n"]
    for w in words:
        out.append("\n" + table("word", w))
    (OUT / "words.toml").write_text("".join(out))

    # ---- tricky_words.toml
    out = [HEADER, "\n"]
    for w, phase, after, src, gpcs in lsdata.TRICKY:
        row = dict(text=w, phase=phase, graphemes=gpcs, source=src)
        if after is not None:
            row["after_order"] = after
        out.append("\n" + table("tricky_word", row))
    (OUT / "tricky_words.toml").write_text("".join(out))

    # ---- sentences.toml
    out = [HEADER, "\n"]
    missing: list[str] = []
    known = {w["text"] for w in words} | set(LEXICON) | {t[0] for t in lsdata.TRICKY}
    for grp in lsdata.CAPTIONS:
        for item in grp["items"]:
            toks = tokenise(item)
            for t in toks:
                if t not in known:
                    missing.append(f"{t!r} in {item!r}")
            out.append("\n" + table("sentence", dict(
                text=item, text_lower=item.lower(), tokens=toks, kind=grp["kind"],
                phase=grp["phase"], after_order=grp["after"], group=grp["group"],
                source=grp["source"])))
    for txt in lsdata.TEXTS:
        for line in txt["lines"]:
            for t in tokenise(line):
                if t not in known:
                    missing.append(f"{t!r} in {line!r}")
        out.append("\n" + table("text", dict(
            title=txt["title"], phase=txt["phase"], after_order=txt["after"],
            lines=txt["lines"], lines_lower=[ln.lower() for ln in txt["lines"]],
            tokens=sorted({t for ln in txt["lines"] for t in tokenise(ln)}),
            source=txt["source"])))
    (OUT / "sentences.toml").write_text("".join(out))

    # ---- lexicon.toml (non-corpus words)
    corpus = {w["text"] for w in words}
    out = [HEADER,
           "\n# Words that are not in the word banks but appear in L&S captions and\n"
           "# sentences, in the DfE Reading Framework's Appendix 7 fixtures, or that\n"
           "# longest-match segmentation would get wrong. The lexicon is authoritative.\n"]
    n_lex = 0
    for w in sorted(LEXICON):
        gpcs, src = LEXICON[w]
        if w in corpus:
            continue
        row = dict(word=w, graphemes=list(gpcs), source=src)
        if any(g in UNTAUGHT_IDS for g in gpcs):
            row["never_decodable"] = True
        out.append("\n" + table("entry", row))
        n_lex += 1
    (OUT / "lexicon.toml").write_text("".join(out))

    print(f"gpcs={len(GPCS)} untaught={len(lsdata.UNTAUGHT)} words={len(words)} "
          f"lexicon={n_lex} tricky={len(lsdata.TRICKY)}")
    n_sent = sum(len(g['items']) for g in lsdata.CAPTIONS)
    print(f"sentences={n_sent} texts={len(lsdata.TEXTS)} "
          f"text_lines={sum(len(t['lines']) for t in lsdata.TEXTS)}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(" ", p)
    if missing:
        print("\nMISSING FROM LEXICON:")
        for m in sorted(set(missing)):
            print(" ", m)


if __name__ == "__main__":
    main()
