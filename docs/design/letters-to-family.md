# Letters to family — design note, v1

> Implementer's design note, 2026-08-23. `docs/plan/SUITE.md` §1 lists this as
> P1 and calls it "the strongest activity in 05"; `docs/research/05-learning-science.md`
> §3 says why, and everything in this note is downstream of the five bullets it
> gives. Everything described here is implemented in
> `activities/letters_to_family/` and asserted in that package's `tests/` unless
> a sentence says otherwise — and where something is **not** built, §7 and §9
> say so in as many words.

## 1. Why this one is worth building properly

`05` §3, verbatim:

> *Evidence: on balance **the strongest activity in the kidnix list.** Purpose
> and audience are the EEF's named mechanism `[GUID]`; extrinsic recognition
> predicts literacy weakly or negatively `[SR]`; social interaction is the four
> pillars' weakest link for a solo product `[SR]`; embedded prompts improved
> outcomes without training the adult `[RCT]`.*
>
> - A real, named recipient from a parent-approved list. The child sees a photo
>   and a name, never an address.
> - Picture + caption + voice. A 5-year-old's letter is legitimately a drawing,
>   three words, and a recorded "I love you Grandad."
> - **Show the reply.** A one-way outbox is not an audience; the reply must come
>   back *into the child's journal* and be announced.
> - A few prompt scaffolds ("tell them one thing that happened today") without
>   templating the letter.
> - **No spelling correction** — invented spelling *is* the Year 1 curriculum.

And `05` §6 #5: *"Purpose and audience are the motivational engine for writing
at 5–7. Letters to family is the strongest concept in the activity list —
**provided the reply comes back**."* The reply is a condition, not a nice-to-
have, which is why §6 of this note exists in v1 at all.

Set against that, `SYNTHESIS` §2 H1: **no network egress from the child session
by default.** The activity whose name most sounds like it needs egress is the
one that must most visibly not have any. So the design is: the child makes a
letter, the machine puts it in a folder, **a grown-up carries it**, and the
program never claims otherwise. That is not a compromise on the evidence —
`05` §6 #10 says the mechanism that works is *designing moments that recruit an
adult*, and a letter that only a grown-up can send is exactly one of those.

## 2. The flow

```
   Who for?   →   Make it   →   Post it            ( + Letters for you )
   a face         a picture     one big button       the shelf of replies
                  then words                         (read-only in v1)
```

Four screens, forwards only, no menu, no tab bar, and **no Back button of our
own** — Back is the shell's, one screen up, in a fixed place in every activity
(`activity-sdk.md` §3.4). B1's flat, spatially stable layout is the reason: a
five-year-old who has pressed Grandad's face should be looking at pictures, not
at choices.

### 2.1 Who for?

A tile per `[[family]]` recipient: the photo if the grown-up gave one and it is
really on disk, otherwise a drawn placeholder; the **name** underneath and the
**name** in the ear ("Grandad" — not "Grandad, your grandpa", and not "Send a
letter to Grandad"). The relation is a note a grown-up wrote to tell two
Grandads apart in the panel; it is not how a child refers to a person they know.

Order is the file's order and is never re-sorted. A pre-reader navigates by
position, and a "who is this for?" screen that reshuffled itself between
sessions would move a four-year-old's Nanna.

**Nobody in the list yet.** A friendly card, one spoken line to the child —
*"There is nobody to write to yet. Ask a grown-up."* — and a `GrownUpTurn` card
for the grown-up they fetch, naming the Parent Panel and the Family tab. The
session ends there and **nothing is written to the Journal**: a card in My
Things for a session in which nobody could write to anybody would be a record of
a failure.

### 2.2 Make it — the picture

Two routes, one screen, five controls (B2's ceiling for a choice screen):

* **Up to four of the child's own recent Journal pictures**, as thumbnails. This
  is the better half of the step and the reason `journal_read.py` exists: the
  strongest version of "make a letter" is not *draw something now*, it is **send
  the dinosaur you were proud of on Tuesday**. The picture is **copied** out of
  the Journal, never linked — the shell rewrites an entry every time a child
  stars it.
* **"Draw one"** — a small press-to-draw canvas, three colours, one big undo.
  Deliberately *not* a paint program: Draw (Tux Paint, tuned) is a whole tile on
  Home and is better than anything that would fit on half of this screen, and a
  second worse one here would be `05` §3's "interface complexity degrades touch
  accuracy" finding arriving by the back door. Three crayons because every extra
  item on a drawing surface costs a five-year-old accuracy; they differ in
  lightness as well as hue (B6). No eraser and no clear-all: repeated undo gets
  to an empty page one stroke at a time, which is recoverable, and a clear
  button is not (C2).

An empty page is still a picture. A four-year-old who pressed "That's it"
without drawing anything meant to, and being sent back would be the program
marking their work.

### 2.3 Make it — the words

The prompt, spoken and written and replayable: **"Tell them one thing that
happened today."** That is `05` §3's scaffold word for word. It is a *prompt and
not a template*: nothing is filled in, there is no "Dear ______", and a child who
writes about something else has not got it wrong.

Three routes, and the child may take none of them:

| | |
|---|---|
| **Write it** | a text box: lowercase, Andika, `NO_SPELLCHECK`, no completion, no red squiggle, no error styling anywhere in the stylesheet. |
| **Say it** | the shell's own twenty-second voice note (`kidnix_shell.voice`): one press starts, a second stops, twenty seconds stops it anyway, a level meter while it runs. **No microphone means no button** — a mic button that does nothing teaches a child that buttons lie. |
| **Ask a grown-up to write it** | a `GrownUpTurn` card with an adult text box in it. Not modal, takes no focus away: an adult who has walked away must not be able to strand a child. |

**Whose words they are is recorded** (`caption_source`: `child` / `grown-up` /
`none`) and shown on the card in different type — the child's own in Andika,
large; a grown-up's transcription smaller and lighter. A reader must be able to
tell whose spelling they are looking at without being told which is better. It
is not a judgement of either.

#### The spelling rule, made mechanical

> **No spelling correction** — invented spelling *is* the Year 1 curriculum.

`Letter.set_caption` is the **only** writer of `Letter.caption` and it does
nothing to the string. Not `.strip()`, not `.capitalize()`, not a spell check,
not a normalisation. `i sor a dinosor  at the parc` — four inventions and a
double space — reaches `caption.txt`, the rendered card and the outbox byte for
byte, and there is a test on each of those three. `draw.py` is checked by AST
(docstrings stripped) for `.capitalize()`, `.title()`, `.upper()`, `.lower()`
and the word "spell", and `activity.css` is checked for `.error`,
`text-decoration` and `underline`.

**One wrinkle, stated rather than hidden.** The SDK's `journal.title_for`
upper-cases the first letter of a short caption when it uses it as the entry
*title* — that is the shell's rule for every activity and not ours to change
here. `caption.txt` and the letter card carry the child's own text unmodified;
only the card's *title* in My Things gets the capital. When there are no written
words the title falls back to **"A letter for Grandad"**, which is a better
thing for a pre-reader's shelf to say than the name of the activity.

### 2.4 Post it

One big button. In order:

1. **Render the letter card** — one PNG with the drawing, the child's own words
   underneath, and "for Grandad" at the top. This is the artefact: what a
   grown-up attaches to an email or prints and puts in an envelope, and what
   makes the card in My Things read as *a letter* rather than *a picture*.
2. **Write the Journal entry** (`kind = "letter"`), with the card first in
   version order and the bare drawing behind it, the caption verbatim, the voice
   note as `note.ogg`, and `meta` carrying the recipient and the status. This
   raises if it fails, and that is correct: `activity-sdk.md` §8 — *"losing the
   thing they just made is the one failure that is not survivable"*.
3. **Copy into the outbox.** Every failure here is logged and swallowed. The
   child's letter is already safe, and a permissions problem on
   `/var/lib/kidnix` must not become "your letter did not work".

Then, spoken and written: **"Posted! A grown-up will send it to Grandad."**

No confetti, no badge, no "well done" (E1/E2) — the letter itself is on the
screen, big, and the sentence names the audience. And **no promise about when a
reply comes**, because nothing on this machine knows and a five-year-old would
hold us to it: `words.py` bans `soon`, `tomorrow`, `shortly` and their friends
from every line, in a test.

### 2.5 Put away

`on_finish` (SIGTERM, five seconds, no dialogue — `activity-sdk.md` §3.3):

* already posted → nothing; a second entry would be the same letter twice;
* a picture but **Post it** was never pressed → kept in the Journal with
  `status = "not posted -- Post it was never pressed"` and **no outbox copy**. A
  grown-up must not find something in the folder they send things out of that
  nobody asked them to send;
* nothing made → nothing kept.

## 3. Recipients — the data contract

Read from the same root-owned file the shell reads, `/etc/kidnix/parent.toml`
first and `/usr/share/kidnix/parent.toml` as the fallback. The schema is the
parent panel's, verbatim — `kidnix_parent_panel.model.Recipient` and the block
`config_io.render_parent_toml` writes:

```toml
[[family]]
id       = "grandad"                          # slug; falls back to a slug of the name
name     = "Grandad"                          # required; what is spoken and shown
relation = "Grandpa"                          # optional; for the grown-up, in the panel
photo    = "/var/lib/kidnix/photos/grandad.jpg"   # optional; missing is normal
```

Top-level `[[family]]`, not `[parent.family]`: the panel's `PanelModel.to_dict`
nests it under `parent` for its own bookkeeping, but the file on the machine has
it at the root, and the file is what we read.

**There is no address of any kind on a `Recipient`** — no email, no phone, no
handle — and a test asserts the dataclass has exactly four fields. An address
field here would be the first half of a feature this product does not have,
sitting in a file a child can read.

Nothing raises. A missing file, a malformed one, `family` that is not a list, a
block with no name, a duplicate id, a photo that has been unplugged: every one
of them is "there is nobody to write to yet" or "that person has no photo", both
of which are screens this activity has and knows how to say out loud.

## 4. The outbox — the data contract

```
/var/lib/kidnix/outbox/<profile>/<YYYYMMDD-HHMMSS>-<recipient-slug>/
    letter.png     the whole letter as one picture — what a grown-up sends
    picture.png    the drawing on its own
    note.ogg       the voice note, if there is one
    caption.txt    the child's words, byte for byte, if there are any
    letter.json    the manifest (below)
```

```json
{
  "schema": 1,
  "recipient": { "id": "grandad", "name": "Grandad", "relation": "Grandpa" },
  "status": "waiting for a grown-up to send",
  "caption_source": "child",
  "picture_source": "journal",
  "has_voice": true,
  "created": "2026-08-23T15:32:00",
  "entry_id": "…",
  "profile": "sam",
  "files": ["caption.txt", "letter.png", "note.ogg", "picture.png"]
}
```

`status` has exactly two possible values and **neither of them is "sent"**:
`waiting for a grown-up to send`, and (Journal only, never in the outbox)
`not posted -- Post it was never pressed`. Nothing in the child session can send
anything, so nothing in the child session writes a third.

The directory name is a timestamp then a name so a grown-up's file manager sorts
chronologically without being asked. The digits are in a path a **grown-up**
reads in Files; 01 #19 is about what a child sees and hears, and no child sees
this.

**Write-only from the activity.** There is no code path here that deletes an
outbox folder, moves one, or marks one sent. Those are a grown-up's.

## 5. The inbox — the data contract

```
/var/lib/kidnix/inbox/<profile>/
    <anything>/           one reply
        from.txt          optional; first line is the sender's name
        <image>           first .png/.jpg/.jpeg/.webp/.gif/.bmp found
        <audio>           first .ogg/.opus/.oga/.mp3/.wav/.m4a/.flac found
        words.txt         (or the first .txt/.md that is not from.txt)
    <anything.png>        a loose file is also one reply, named from its stem
```

* **The sender's name** comes from `from.txt` if there is one, otherwise from
  the folder or file name with numeric segments dropped:
  `2026-08-23-grandad/` → "Grandad". Dropping the digits is not tidiness — it is
  01 #19: that string is spoken to the child.
* **Newest first** by mtime, capped at eight.
* Dot-files and anything that is not a picture, a sound or words are ignored.
* **Read-only.** Nothing in the activity writes into the inbox, marks a reply
  read, or moves one. A test lists an inbox and asserts nothing in it changed.

## 6. "Letters for you" — the reply

A shelf button appears on the first screen (and on the posted screen) whenever
there is a letter to show. Pressing it shows a tile per reply — the card, the
picture, or the placeholder, with the sender's name; pressing a tile shows it
big, prints the words, and offers **Listen** for a voice reply. It is a way in
and not a dead end: **Write a letter** under the tiles goes back to "Who is
your letter for?" with a clean sheet.

**What it reads is the Journal** (§7 step 5, 2026-08-24): the shell's imported
`letter-reply` cards for this child, newest first, capped at eight — with the
inbox read underneath only for a reply that arrived since the last sweep, and
the two deduped by the inbox path `meta.json` recorded. v1 read the inbox
directly, which meant a letter the child had already been given never left the
shelf.

The button never says how many. A count is a digit on a pre-reader's screen and
it is also the shape of a notification badge, which D6 says this product does not
have. One letter and nine letters get the same three words, and the child finds
out how many by looking.

`05` §3 — *"the reply must come back into the child's journal and be
announced"* — is §7, and it is shipped.

## 7. Importing a reply into the Journal — shipped

`05` §3 says the reply must come back *into the child's journal* and **be
announced**. v1 showed the reply and did neither. Both belong to the shell, not
to an activity, because the announcement is Home's and because a reply must be
there whether or not the child opens Letters.

The contract, and where each point landed:

1. **Where — shipped** (`kidnix_shell/inbox.py`).
   `/var/lib/kidnix/inbox/<profile>/`, as §5 above. The shell **sweeps** it at
   "Who's here?", so the card exists before Home is built; not inotify — a
   reply is not urgent, and watching `/var/lib` from the child's session is a
   permissions question nobody needs to answer for something that can wait
   until the next sitting.
2. **What to write — shipped.** One Journal entry per reply directory (or loose file),
   `kind = "letter-reply"`, using `kidnix_activity.journal.save_entry`'s layout:
   the image as `v001.*`, `note.ogg` for the audio, the words as `caption.txt`,
   and `meta.json` carrying `{"from": "<name>", "source": "<inbox path>"}`.
3. **Idempotence — shipped**, twice over: the state file below is the fast
   answer, and the Journal's own `source_path` index is the backstop, so
   deleting the state file still imports nothing twice. Import once and only
   once. The inbox is *not* emptied by the import — it is a grown-up's folder
   and the child's session has no business deleting from it. So the shell keeps a small state file of already-imported
   paths (path + mtime + size, the same triple `JournalImporter._stat` already
   uses) under the profile's state directory.
4. **Announcing — shipped** (`inbox.Announcement`, taken once at the first
   Home of the sitting). The shell's own business: a spoken line on Home, once per
   session, naming the sender. It must not be a badge, a count, or a
   notification (D6), and it must not be a reason to come back to the machine —
   the system has no interest in whether the child returns.
5. **This activity's shelf reads the Journal instead of the inbox — landed
   2026-08-24.** `letters_to_family.journal_read.letter_replies` lists this
   child's `kind = "letter-reply"` entries, newest first, and
   `shelf_replies` is what "Letters for you" is built from. The inbox is now
   purely a grown-up's drop point.

   Reading the folder was the wrong end of it: nothing in the inbox is ever
   marked read — the child's session cannot write there and must not — so a
   reply the shell had already put in My Things sat on the shelf as well, and
   for good. "The child has already been given this one" is a fact only the
   shell has, and it has it by having imported the letter.

   Two details the implementation pins:

   * **The inbox is still read, as a fallback only.** A reply that arrived
     since the last sweep (a grown-up dropping a folder in while the child is
     at the machine) would otherwise be invisible until the next login. The two
     lists are deduped by `meta.json`'s `source`, which is the inbox path the
     shell imported, and the Journal's copy wins because it carries the card
     and the sender's name.
   * **The card is the tile.** `thumb.png` beside the entry is the picture
     scaled to 256 px, or the envelope the shell drew for a letter that is only
     words or only a voice — so a shelf of voice notes is six letters and not
     six placeholders.

   Still read-only in both directions: this activity does not import, delete,
   move, or mark anything.

## 8. What the image wave has to do

1. **The tmpfiles fragment — shipped** (2026-08-23, with the wave that installed
   Numbers and Clock): `system_files/usr/lib/tmpfiles.d/kidnix-letters.conf`.
   `/var` is machine-local in a bootc image, so neither directory can travel in
   the container:

   ```
   d /var/lib/kidnix        0755 root   root -
   d /var/lib/kidnix/outbox 0750 kid    kid  -
   d /var/lib/kidnix/inbox  0750 parent kid  -
   ```

   The modes are the policy. The **outbox is the child's**: they write it, and
   `0750 kid:kid` keeps a five-year-old's letters off every other login on the
   box — a grown-up reads them through the parent account, which is in `wheel`,
   the same route they take to everything else of their child's. The **inbox is
   the grown-up's**, in the other direction: they drop a reply in, the child's
   activity reads it, and `kid` gets `r-x` and no more, so the child cannot
   write a reply to themselves. That is an honesty boundary rather than a
   security one — the "Letters for you" shelf must only ever show something a
   person actually sent. Both are `d` and never `C`: an upgrade must not seed,
   clear or reset either.

2. **Install the package and the manifest** — still to do: `cp -a` the
   `letters_to_family` package into `/usr/lib/kidnix/` beside the shell (as
   `build_files/60-shell.sh` does for `kidnix_activity`), the console script to
   `/usr/bin/kidnix-letters`, and `manifest.toml` into
   `/usr/share/kidnix/activities/`. Until that lands the tile does not exist,
   which is correct: a tile that opens a half-built activity is worse than an
   absent one.

3. **Nothing in the firewall.** `network_required = false`, there is no socket
   in the package, and the child session's egress stays denied (H1). If anybody
   ever proposes an allow-list entry "just for Letters", the answer is in §1.

## 8a. Two rules the development entry points keep

**No sound on a developer's machine** (AGENTS.md §5). `KIDNIX_SPEECH=off`
already gives `kidnix_shell.speech` a null voice — but the **earcons are a
second audio path** (GStreamer straight to PipeWire) and nothing in the SDK
reads that variable for them. So `letters_to_family.env.quiet()` reads the same
variable and `main()` hands the application a disabled `Earcons`: one switch,
both channels. `tests/conftest.py` sets it for every test in the package, the
GTK smoke test additionally injects a disabled earcon set, and the Justfile
exports it for every recipe.

**No window on a developer's desktop** (`activity-sdk.md` §10). `just run`,
`just test-gtk` and `just screenshots` each start their own `gtk4-broadwayd`.
Note there is **no `-p`**: the daemon derives its port from the display number
(8080 + N) and so does the client, so forcing one makes the daemon listen where
GDK will never look — which presents as "GTK would not initialise" and cost an
hour here.

**Neither `--screenshot` nor the GTK tests call `Gio.Application.run()`.**
`run()` registers on the session bus before it activates anything; with no
reachable bus — a build container, a sandboxed runner, a terminal outside the
developer's own session — `g_application_register` spends the D-Bus default
timeout (**25 s, measured**) failing and then returns *without activating*. Both
call `do_activate()` and own the main loop themselves. The shipped path,
`kidnix-letters` with no flags, is `app.run()` exactly as every other activity.

## 9. Still open after this pass

1. **The reply does not reach the Journal yet** (§7). The shelf makes the path
   visible; the import is a shell change and is specified above, not built.
2. **The parent panel has no outbox view.** A grown-up finds letters in Files
   at `/var/lib/kidnix/outbox/<profile>/`, which is F4's boring conventional
   artefact and is honest, but a "Letters waiting" row on the Family tab with an
   Export button is the obvious next thing. The panel's Family tab currently
   says "data only"; that sentence will need changing when it lands.
3. **No print.** `SYNTHESIS` F3 lists Print beside Send to family as a Journal
   card action, and a posted letter is precisely the thing a household would
   want on paper. It belongs to the Journal card, not to this activity.
4. **The canvas has no pressure or velocity.** `05` §3's drawing bullet wants
   line width to follow pressure where the hardware allows. Tux Paint is where
   that belongs; this canvas is three crayons and one width, on purpose.
5. **No resume.** `meta.json` is written and nothing reads it back, exactly as
   `activity-sdk.md` §13 #5 describes for every SDK activity. A child cannot
   open a posted letter from My Things and add to it, and it is not obvious that
   they should be able to.
6. **The SDK ends `caption.txt` with a newline.** `kidnix_activity.journal`
   writes it that way for every activity, so the Journal copy of a child's words
   has one character this package did not put there. The *characters* are theirs
   — nothing is cased, stripped or corrected — and the **outbox** copy, which
   this package writes itself, is byte for byte. Worth knowing before anybody
   diffs the two and concludes the caption was touched.
7. **`kind = "letter"` is not yet a vocabulary.** `activity-sdk.md` §13 #4 wants
   `picture` / `writing` / `sound` / `tune` to become a closed set the Journal
   can filter on; `letter` and `letter-reply` want to be in it when it exists.
8. **One recipient per letter.** No "and Nanna". Two names on one envelope is a
   real thing households do and it is a second selection state on the first
   screen, which is a choice a four-year-old does not need on day one.
