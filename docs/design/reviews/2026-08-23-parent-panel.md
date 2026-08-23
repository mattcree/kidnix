# Parent panel review — 2026-08-23

Four invented parents, shown the same material: the README and its screenshots,
the Home tiles and their goal lines, `parent.toml` and `session.toml`,
`docs/BUILDING.md`, `PRIORITIES.md`, `HARDWARE.md`, `CHILD-TEST-PROTOCOL.md`,
and the plain-language walk-through below. They are composites, not real people;
they are here to catch the things a team building this cannot see any more.

---

## What they were told first (the plain-language summary)

> kidnix turns one laptop into a computer that belongs to your child and does
> nothing else.
>
> They switch it on and it goes straight to **"Who's here?"** — they tap their
> own name. Next it asks **"What's next after?"** and they pick, from pictures,
> what they will do when the computer is finished: outside, a book, a snack,
> bath. Then **Home**: a handful of big picture buttons — Draw, Potato faces,
> Letters & numbers — that speak their own names when your child rests the
> pointer on them. One thing at a time; no windows, no desktop, no files.
>
> A **sun** sits along the top. It shrinks and sinks as the session goes. Around
> six minutes from the end the computer *offers* to finish; two minutes out it
> says **"put your things away"**; then it says goodbye and reminds them of the
> thing they chose earlier — "Ready to go outside?" Then the screen goes to
> **Sleeping** until next time. The computer ends it, not you.
>
> Everything they make lands in **My Things** — a scrapbook grouped as Today,
> Yesterday, Before. Not folders, not filenames.
>
> There is a **grown-up button** in the corner. Hold it, type a PIN, and you can
> start a session, add ten minutes, or end it now.
>
> **Your child cannot reach the internet.** Not filtered — switched off for
> their account. Nothing phones home. No adverts, no accounts, no videos, no
> shop, no points or streaks. You get a normal desktop on a separate login.
> Updates happen when you ask for them.

Everything below is a reaction to that, plus what they found when they looked.

---

## A — Priya · working mum, two children (5 and 7), one laptop

**First impression.** The pictures are lovely — calm, big, obvious, nothing
flashing at my kids. What made me stop was "the computer ends it, not you",
because ending screen time is the worst ten minutes of my day. Then I realised
this is not an app I install on a Sunday night — it is a whole operating system
that eats a laptop, and we have one laptop and I work on it.

**What she'd love.** The ending ritual, first and last. A warning at six
minutes, "put your things away" at two, then a goodbye that reminds them what
comes next — that is the script I try to say and never manage consistently. The
25-minute session and the 60-minutes-a-day ceiling being decided once, in
advance, by something that is not me. Home showing only a few things so my
five-year-old isn't paralysed. And no YouTube. No YouTube is most of the pitch.

**What worries her.** There is one child in `parent.toml` and she is called
"Me". I have two, two years apart, and they will fight over whose computer it is
and whose drawings those are. The age band is set to 4–5, which would hide the
number game from my seven-year-old — so do I edit a settings file between them?
Is the 60 minutes a day *each*, or shared? Bedtime starts at 19:00, when my
eldest is still finishing reading homework. And the honest one: it needs its own
machine, and a refurbished laptop is £150 I have not budgeted.

**What she doesn't understand.** How I get it. The README says `just ci` and
`just build-qcow2` and I don't know what any of that is. Whether "immutable"
means my kids can't break it or means I can't fix it. What "the Journal" is — is
it a diary? And whether installing it wipes the laptop (it does, and nobody says
so in words I'd recognise).

**Three questions she'd ask.**
1. Can both of my children use one machine, with their own names, their own
   time, and their own drawings — without me editing anything?
2. Is the daily hour per child or per computer, and can I give ten more minutes
   on a rainy Saturday without a whole performance?
3. Do I need to buy a second laptop, and can someone else set it up?

**Would she try it?** Maybe — not this month. Only once it runs two children,
and only if it arrives on a machine already set up.

**The one change that would move her.** Two named children, each with their own
colour, time budget and My Things — set up from a screen, not a file.

---

## B — Dan · dad of an autistic five-year-old

**First impression.** I read "What's next after?" and said something out loud,
because that is a first-then board — the thing his speech and language therapist
has had us doing on the fridge for two years — and nobody has ever put it inside
the computer. Then the goodbye screen shows the picture back and says "Ready to
go outside?", which is the whole trick, and someone here knows it. Family Link
gave me a bar chart and a lock; this gives him a plan.

**What he'd love.** That the ending belongs to the machine and not to me, so I
am not the person taking it away. The same screens in the same order every time.
Nothing that scores him — no streaks, no badges, nothing that makes stopping
feel like losing. Read-aloud, because he can't read yet and hates being asked
to. That the ending is a ritual with three named steps, not a screen going
black.

**What worries him.** Three things, and they are all the same thing.

First, **Home grows.** Six tiles, then one more every two sessions. A new button
appearing without warning is not a delight, it is Tuesday ruined. There may be a
way to stop it — something about `show_everything` and an allow-list — but
working that out means reading two config files that cite research papers at me,
and I will get it wrong at 7am.

Second, **the ending has a stranger in it.** In the picture strip, when the
computer asks Tux Paint to finish, Tux Paint puts up *its own* box — different
colours, a green tick and a pink cross — and waits for him to press it. So the
calm predictable ending contains a surprise dialogue in another program's visual
language, and the pink cross deletes the drawing. That is where we'd lose him.

Third, **sound**. Everything speaks, there are little sounds, one game has
music, and there is no volume or quiet button anywhere I can see. Sound is his
biggest sensory trigger. "Calm mode" is roadmap, not product.

**What he doesn't understand.** Why the screen grows at all. Whether the
six-and-two-minute warnings can be lengthened. What the sun actually tells him:
it shrinks and sinks, but does that say *how much is left*, or only that time
passes?

**Three questions he'd ask.**
1. Can I lock the screen so it never changes without me doing it?
2. Can I make the ending longer, and can he have a countdown he understands
   rather than a sun?
3. Can I turn all the sound down in one place?

**Would he try it?** Yes — the most willing of the four. This is closer to what
he needs than anything he has been sold.

**The one change that would move him.** One switch called "keep everything the
same": fixed tiles in a fixed order, no new tiles ever, no activity's own
dialogue reaching him, adjustable warning times — and no config file to get it.

---

## C — Mags · grandmother and guardian, six-year-old grandson

**First impression.** My first thought is that he'd be better off with a book,
and I notice the computer agrees — "A book" is one of the choices for what he
does next, which softened me more than anything else on the page. My second is
that this is built by clever people for other clever people; the first thing
under the picture is a list of commands. My third, the one that stays: what
happens when it goes wrong and I'm the only adult in the house?

**What she'd love.** That nobody can talk to him and he can't wander onto the
internet. That it stops on its own after twenty-five minutes and won't start
again after seven in the evening. No shop, no adverts, nothing collecting
information about him — I've had enough of that. That what's kept is his
drawings, not a report on how many hours he sat there. And that it looks quiet:
cream and green, not fireworks.

**What worries her.** The PIN. It comes set to **1234**, it is written down in
the instructions, it is the same on every one of these, and as far as I can tell
there is no way for me to change it without someone doing something technical.
My grandson is six. He watches me type. 1234 is the first four buttons in a row.
That is not a lock, that's a sticker on a door.

Under that, the bigger worry: getting it wrong. If it won't start on a school
night, I have nobody to ring. Words like "rollback" and "immutable" make me feel
I'd need permission to touch it.

**What she doesn't understand.** Almost all of the building instructions —
fine, they're not for me, but there is nothing that *is* for me. What "the
Journal" is (I thought a diary; it's his drawings). Whether pulling the plug out
is safe. Whether "no internet for the child" means the machine is off the
internet or just him — and how I would ever check.

**Three questions she'd ask.**
1. What do I press when something goes wrong, and is there one page I can keep
   by the kettle?
2. Can I pick my own PIN, on the first day, without help — and can he see me
   type it?
3. How do I know, for myself, that he can't get onto the internet?

**Would she try it?** No — not yet. Not without a person to set it up and a
printed page. She'd say yes to a demonstration.

**The one change that would move her.** It asks her to choose her own PIN the
first time it's switched on, and there's one printed page: what the screens
mean, what to press, what to do if it won't start.

---

## D — Tom · software-literate dad, four-year-old daughter

**First impression.** This is the first thing in the category I've read that
isn't a data-collection business with a cartoon on it — no telemetry, no
accounts, network switched off by user id rather than by a filter that fails
open, Apache-2.0, signed images, decisions written down. The manifests are
startlingly honest: "UNVERIFIED", "inferred, not observed", "nobody has watched
it produce a qcow2 yet". I trust that more than a polished claim. Then I hit the
line saying the kiosk currently launches a text editor as a placeholder, and
realised the docs are behind the shell — usual day-one stuff, but it wobbled me.

**What he'd love.** No egress for the child's account, enforced under the
session rather than inside it. Zero telemetry. Everything configurable in plain
TOML I can read, diff and back up. Open formats in the Journal — PNGs, not a
database. Atomic updates with rollback, genuinely better than my own laptop
does. And the refusal list: no browser, no store, no video, no chat, no points,
no generative AI in the child session.

**What worries him.** Four things, roughly in order.

*Updates.* There is no update mechanism on the device — no unit, no timer, no
button, no notification. "Parent-driven" today means me remembering to SSH in. A
machine in a playroom corner will sit unpatched for a year.

*Getting locked out.* The build notes say an image installed without a password
leaves the `parent` account locked. That's my laptop and my child's drawings
behind a door I can't open.

*Adding things.* Activity manifests live in `/usr/share`, which the image owns
and every upgrade replaces. So "can I add an app?" today means "fork and rebuild
the image" — a hobby, not a feature.

*Getting her work out.* Her drawings sit in the child account's home directory
and I'm a different user. No printing, no export, no "send to Granny" — all
roadmap. That was going to be the thing that sold this to my mum.

Minor, but he'd say it: PIN 1234 with a fixed public salt in a public repo means
the hash is decorative and identical everywhere.

**Three questions he'd ask.**
1. How does an update reach this machine, who notices, and what happens the
   morning after a bad one?
2. What's the supported way to add an activity that survives an upgrade — a
   drop-in directory, or do I fork?
3. Where do her drawings physically live, and how do I get one onto paper and
   into an email to her grandmother?

**Would he try it?** Yes — in a VM this weekend. On real hardware once there's a
parent panel and an export path.

**The one change that would move him.** A supported way in and out: a drop-in
directory for activities and content that upgrades don't clobber, and an export
folder the parent account can read and print from.

---

## Panel summary

### Shared themes

**Everyone loved the same two things, and they are the same thing.** The
machine-owned ending and "What's next after?" won all four parents
independently. Priya wants to stop being the villain, Dan wants a first-then
board, Mags wants a hard stop, Tom likes that it's honest about being a limit.
Nothing else in the product got a unanimous yes. This is the product.

**Everyone stopped at the same wall: there is no way in.** All four asked some
form of "and then what do I press?", and all four found the answer is a TOML
file. The gap between the care in the child's experience and the total absence
of a parent's experience is the single loudest note in this review. The PIN is
the sharpest edge of it — 1234, public, identical everywhere, unchangeable
without writing code — and two of four parents named it unprompted.

**Three of four cannot use it on the hardware they own.** It takes a whole
laptop, installed by a developer. Priya has one laptop and works on it. Mags
would need a person. Tom will use a VM. Only Dan is willing to buy a machine for
it, and he's the one being asked to buy the most trust.

**Predictability is a feature that is currently a config file.** Dan needs the
grid never to change; the mechanism to achieve that exists (allow-list plus
`show_everything` plus `initial_tiles`) but requires reading two annotated
config files and reasoning across them. A feature a parent cannot find is not a
feature.

**"What can she make, and can anyone else see it?"** Priya, Mags and Tom all
arrived at output — drawings on the fridge, a picture posted to a grandparent, a
thing that leaves the screen. The Journal is well built and currently a dead
end.

**Nobody asked about the shell, the compositor, the image, or the research.**
Not once.

### Top 5 asks, in priority order

1. **A parent panel — even a bad one.** Children (add, name, colour, age band),
   Time (session, daily budget, bedtime), Activities (which tiles), and a PIN
   the parent sets on first switch-on. Nothing here is technically hard; its
   absence is what stops three of four parents. Set the PIN first: the shipped
   1234 is the review's single most-cited defect.
2. **Two children on one machine.** Own name, own colour, own time, own My
   Things, switchable without a settings file. Blocks Priya outright and would
   block most families with more than one child.
3. **A "keep it the same" switch, and a quiet one.** One control that freezes
   the tile grid, lets a parent set the warning times, and turns the volume down
   in one place. Serves the child who needs it most and costs the others
   nothing. Related and concrete: Tux Paint's own quit dialogue appearing inside
   the ending ritual breaks the ritual's promise — either handle it for the
   child or don't ship an ending that a different program can interrupt.
4. **A way out for the child's work.** An export folder the parent account can
   read, then printing, then send-to-a-grandparent. Three of four parents got
   here on their own, and it is the thing that makes the machine feel like it
   makes things rather than contains them.
5. **An install-and-update story for a parent.** An ISO you can follow, an
   account you can't get locked out of, updates that arrive on the device with a
   button and a notification, and one printed page: what the screens mean, what
   to press, what to do when it won't start.

### Things the team is proud of that parents don't care about

- **bootc, atomic upgrades, image-based OS.** Only Tom noticed; the other three
  read "immutable" as "I can't fix it", which is worse than neutral.
- **The build and CI loop** — `just ci`, the boot test, rootless podman, the
  bcvk install rationale. Three of four parents opened `BUILDING.md`, found
  nothing addressed to them, and closed it. It is currently the first door and
  it has no handle.
- **The research provenance.** The citations in `parent.toml` (Coco's Videos,
  Pailian, Paulus & Remijn) are the best argument the project has and they are
  in a file no parent will open. They belong on the page a parent reads first,
  in one sentence each, and nowhere near the settings.
- **The 450 ms hover dwell, the sun's geometry, the 18 pt label floor, the
  SIGTERM analysis per activity.** Superb work; invisible by design; correctly
  invisible. Nobody mentioned any of it. That is a success, not a complaint —
  but it means none of it earns the project a parent, and the effort spent there
  is not spent on the panel.
- **"No web browser, no store, no feeds" as a technical achievement.** Parents
  care enormously about the *outcome* and not at all about how it was enforced —
  except Tom, who wanted to verify it. Mags asked how she could check for
  herself, which is the useful version of this: a plainly-worded, verifiable
  claim, not an architecture.
