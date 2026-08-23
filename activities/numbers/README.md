# Numbers

The kidnix subitising and number-bonds activity. Two questions, eight items,
about eight minutes:

1. **How many?** A picture flashes and goes; the child presses the numeral.
   One to five in canonical dice arrangements, and — where a grown-up has set
   the range — six to ten as a full row of five and some more on a ten-frame.
2. **Make five, make ten.** Some counters are in a frame; the child fills the
   empty boxes or presses the number that is missing, and the pair is said out
   loud: *"three and two make five."*

Then a card addressed to the grown-up, and a picture of what was practised into
the Journal.

Built to one statutory paragraph — the [EYFS Number
ELG](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2):
subitise up to 5, number bonds to 5 and some to 10 including doubles. The design
note is [`docs/design/numbers.md`](../../docs/design/numbers.md); the evidence is
`docs/research/05-learning-science.md` §2c.

**No score, no star, no streak, no level, no timer.** A wrong answer is never
called wrong: the picture comes back and the dots get counted, twice at most,
and then the child is told. Difficulty never moves on its own.

## What a grown-up can set

`/etc/kidnix/numbers.toml` (the shipped default is `numbers.toml` here):

| Key | Values | Default |
|---|---|---|
| `range` | `"five"`, `"ten"` | `"five"` |
| `numerals` | `true`, `false` | `true` |
| `frames` | `"auto"`, `"five"`, `"ten"` | `"auto"` |

## Working on it

```bash
just setup        # venv with --system-site-packages
just test         # everything; GTK tests skip without a display
just test-headless# the CI floor: no display, no SDK needed
just test-gtk     # the window, under Broadway -- never your desktop
just lint
just validate     # the manifest, with the image build's own validator
just run          # the activity, under Broadway
just screenshots  # docs/design/screenshots/numbers-*.png
just ci
```
