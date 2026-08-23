# Activity tile icons — brief, rationale and acceptance test

**Status:** drawn, wired into the manifests, not yet tested on children.
**Files:** `shell/kidnix_shell/data/icons/kidnix-act-*.svg`
**Proof sheet:** `docs/design/screenshots/icons-contact-sheet.png`
**Sources:** forum #19 (cci-researcher), #35 (early-years-teacher), #37
(accessibility-specialist), #50 (childrens-ux-designer);
`docs/design/reviews/2026-08-23-childrens-ux-designer.md` §4 and B1/B2.

## The finding this answers

Every shipped manifest pointed at a **vendor logo**: `tuxpaint` → a penguin,
`klettres` → the KDE flag, `gcompris` → a brand swirl, `turbowarp` → the
TurboWarp mark. For a pre-reader the written label is noise and the spoken label
is transient, so **the picture is the only persistent channel** — and a penguin
does not mean *draw*.

Worse (#37): `widgets.icon_image()` falls through to `category_icon(category)`
when the theme has never heard of the name, which under Flatpak is the likely
path, not the edge case. Every `make` activity then collapses to one bundled
pencil and every `learn` activity to one bundled book — five of six tiles, two
pictures. For a child with low vision or CVD the tile carries no distinguishing
information at all.

**The rule adopted (forum #35):** the icon shows the **output** or the **action**,
never the tool. That is what the child is choosing between.

## The ten, and why each is drawn the way it is

| File | Tile | What it depicts | Why |
|---|---|---|---|
| `kidnix-act-tuxpaint.svg` | Draw | Paper with a wet pink stroke already on it; a fat amber brush, teal bristles, on the diagonal | The **output** is a picture that exists. Deliberately a brush, not a pencil: `kidnix-next-draw` already owns pencil-on-paper and the two must not collide. |
| `kidnix-act-ktuberling.svg` | Potato faces | Tan potato, eyes and nose stuck on **askew**, one eye visibly rotated, a loose ear waiting beside it | The askewness *is* the activity. A tidy face would read "a face"; a crooked one plus a spare part reads "you stick these on". |
| `kidnix-act-gcompris.svg` | Letters & numbers | Three play-blocks, two-and-one: `a`, `3`, one blank | Blocks say *manipulable*, which is what GCompris is. The blank third block says "and more of these". |
| `kidnix-act-klettres.svg` | Letter sounds | A head in near-profile, mouth open, two teal sound arcs, a lowercase `a` riding the outer arc | **Sound**, not shape, is the only thing separating this tile from Letters & numbers. Without the mouth these two would be the same icon. |
| `kidnix-act-blinken.svg` | Copy the lights | Four pads 2×2, three slate, one amber with a dashed glow ring | One lit out of four is the whole game in one picture, and it survives greyscale (the lit pad is the only light one). |
| `kidnix-act-tuxmath.svg` | Number game | Three beads on a wire between two posts, two pushed left, one right | Counting, partitioned. **No arithmetic symbols**: a pre-reader can no more read `+` than a word. |
| `kidnix-act-kolf.svg` | Mini golf | Ball mid-roll with two motion ticks, a green band, the hole cut into it, pink flag | The goal, not the equipment. |
| `kidnix-act-supertux.svg` | Jump and run | A child-shaped figure airborne, limbs mid-stride, a platform under each side and clear air under both feet | A figure, not a mascot. Both feet clear of both platforms is what makes it a *jump* rather than a *stand*. |
| `kidnix-act-turbowarp.svg` | Make a game | A teal and a pink instruction block snapped together, an amber arrow leaving the lower one | ScratchJr's own solution and it reads without a word: blocks in, movement out. |
| `kidnix-act-kiwix.svg` | Library | Three books leaning on a shelf, the front one pulled half-out with a picture on its cover | Not a magnifying glass — that means *search*, which means *reading*. The picture on the cover says what you get. |

Plus `kidnix-act-all-done-day.svg` — see below.

### Deviations from the §4 brief, and why

1. **Kolf loses the putter.** §4 asked for "ball, short putter, flag in a hole".
   The putter is the *tool*, which #35's rule excludes, and at 15 mm a third
   object in the frame was the difference between reading and not.
2. **Letterforms are kept**, despite §4's own "no text, digits or brand marks"
   sentence contradicting its own table. `a` and `3` are the *subject matter* of
   a letters-and-numbers activity, not a label. They are drawn as **paths**, never
   `<text>`: no font is guaranteed on the image, and Andika in particular is not,
   so a `<text>` element would render in whatever fallback exists or in nothing.
3. **Both `a`s are single-storey with no ascender.** The first draft put the stem
   above the bowl and it read unmistakably as a `d` at every size. Caught on the
   contact sheet; fixed.
4. **The category badge (`kidnix-make` / `-learn` / `-play` at 14 px, 40 %) is not
   here.** That is a tile-composition change in `widgets.py`, not an icon.

## How they are wired

Each manifest now carries:

    icon = "kidnix-act-<id>"
    icon_kind = "icon-name"

`<id>` is the manifest's own `id`, so the mapping is mechanical and a future
`--validate-manifests` rule can assert `icon == "kidnix-act-" + id` in one line.

The panel asked for `icon_kind = "path"`. `"path"` requires an *absolute* path,
and the bundled icons have no stable one — `build_files/60-shell.sh` installs the
package into `sysconfig`'s purelib, so they live at
`/usr/lib/python3.14/…/kidnix_shell/data/icons/`, Python version and all. A
rebase to Python 3.15 would turn every tile into `image-missing`. The
`kidnix-act-` name is a private namespace no icon theme ships, so
`widgets.icon_image()` misses the theme and lands on `bundled_icon()` — this
directory — every time. Verified: all ten resolve, to ten **distinct** files.

Full reasoning, and the case for adding a `"bundled"` `icon_kind` that makes this
explicit, is in `shell/kidnix_shell/data/icons/README.md`.

## "All done" — `kidnix-act-all-done-day.svg`

The Home "All done" tile currently uses `kidnix-moon` (`screens/home.py:75`,
asserted at `tests/test_gtk_smoke.py:288`). A moon means *night* on a tile a child
presses at ten in the morning, and it is the same picture the Sleeping screen
uses, so one image means two things.

The daytime variant draws what pressing it *does*: a picture tilted, going down
into a teal box, motion ticks either side. Distinct from `kidnix-my-things`
(amber box, pictures already in it, no motion) by colour, tilt and movement.

It is **offered, not switched on** — `home.py` and its test are shell code owned by
someone else, and they must change together.

## Acceptance test (from the UX review, §5 Q2)

Drawing these took a day. **Judging them is the part that fails**, so:

1. Print all ten at **15 mm** — the size they occupy on a 10" screen at a child's
   arm's length. No labels. No sound. No colour cues from the tile behind them.
2. Hand them to **four children aged 4–6**, one at a time.
3. Ask, of each icon: **"What would happen if you pressed this?"**
4. Score a hit when the answer names the activity or its output — "you draw a
   picture", "you make a funny face", "you jump" — not when it names the objects
   ("a brush", "a potato").
5. **Below 3 of 4, the icon is redrawn.** Not renamed, not explained, not
   defended: redrawn.

Two checks that can be run *before* the children, and were:

* **Silhouette and greyscale at 40 px.** Both are on the contact sheet, columns 4
  and 5. An icon that dies in greyscale carries nothing for a child with CVD, and
  the label is then the only channel left — which B4 says must never happen.
* **Pairwise distinctness.** The two literacy tiles (`gcompris`, `klettres`) and
  the two "figure" tiles (`ktuberling`, `klettres`) are the collision risks, since
  four of the ten are learning activities and all collapse into books if drawn
  lazily. Check those four side by side first.

## Re-rendering the contact sheet

librsvg is available through GObject introspection (`gi.repository.Rsvg`) plus
`pycairo` and Pillow; `rsvg-convert` and `inkscape` are **not** installed on this
machine. The sheet renders each icon at 128 px, 64 px, 40 px, 40 px greyscale and
40 px silhouette:

```python
import gi; gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg
import cairo
from PIL import Image

h = Rsvg.Handle.new_from_file(path)
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, px, px)
ctx = cairo.Context(surf)
rect = Rsvg.Rectangle(); rect.x = rect.y = 0; rect.width = rect.height = px
h.render_document(ctx, rect)
img = Image.frombuffer('RGBA', (px, px), bytes(surf.get_data()),
                       'raw', 'BGRA', surf.get_stride(), 1)
```

This also doubles as a **parse check**, and it found a live bug: `kidnix-finish.svg`
has ` -- ` inside an XML comment, which is not well-formed XML, so librsvg refuses
the file outright. The band's "Finish this one" icon is not rendering. One-character
fix, left to the band-icon owner.
