from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from sounds_and_words.ceiling import custom_ceiling
from sounds_and_words.corpus import load_corpus

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def corpus():
    return load_corpus()


@pytest.fixture(scope="session")
def appendix7():
    with (FIXTURES / "reading_framework_appendix7.toml").open("rb") as fh:
        return tomllib.load(fh)


@pytest.fixture(scope="session")
def appendix7_ceiling(corpus, appendix7):
    f = appendix7["fixture"]
    ids = set(f["alphabet_gpcs"]) | set(f["named_gpcs"]) | set(f["added_gpcs"]) | set(
        f["footnote_variant_gpcs"]
    )
    return custom_ceiling(
        corpus,
        ids,
        scheme="reading_framework_appendix7",
        label="Reading Framework Appendix 7",
        tricky_words=set(f["exception_words"]),
        notes=("DfE Reading Framework 2023, Appendix 7, pp.144-145.",),
    )
