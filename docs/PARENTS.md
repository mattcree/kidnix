# kidnix — the page to keep by the kettle

This page is for the grown-up. It is one page on purpose. Nothing in it needs a
password, a terminal, or anyone clever.

If you only read one line: **kidnix turns one old laptop into a computer that
belongs to your child and does nothing else.**

---

## What it is

An old laptop with kidnix on it starts up straight into your child's things.
There is no login for them, no desktop, no icons to lose, no shop, and **no web
browser at all** — not hidden, not blocked, not installed.

They see a screen of large pictures: Draw, Potato faces, Letters and numbers,
Copy the lights, and a few more. They press one. It fills the screen. When
they are finished, the computer says so and puts it away.

That is the whole machine.

## How a session goes

1. You open the lid. It starts up into your child's screen. No password.
2. They pick something and do it.
3. After the time you have set (25 minutes to start with) the screen tells them
   the session is ending, gives them a warning first, then finishes.
4. The picture they were drawing is saved on the way out. They are never asked
   "do you want to save?" — a five-year-old cannot answer that question.

**The sun in the corner** shrinks and sinks as the session goes on. It is a
"there is less left than there was" signal, not a clock — a child who cannot
read numbers can still see it move. It is not meant to tell them exactly how
many minutes remain.

**Pulling the plug out is safe.** It is not a computer that has to be shut down
properly. The picture they were working on may be the last thing lost, and
nothing else is.

## The PIN: do this first, before they touch it

There is a grown-up gate. Press and hold the plain corner tile for three
seconds, type four numbers, and you are in the grown-up settings.

**The machine ships with no PIN at all, and the first person to reach the gate
chooses it.** So the first thing to do on a new machine, before you hand it
over, is:

1. Hold the plain corner tile in the bottom corner for three seconds.
2. The screen asks you to choose a grown-up PIN. Type four numbers, twice.
3. That is it — it is saved on the machine and it is the PIN from then on.

**Do it somewhere your child cannot watch your fingers.** A six-year-old who
has seen you type four buttons has your PIN, and that is the actual threat
here, not a stranger guessing. Avoid 1234 — the machine refuses it, because it
is what kidnix used to ship with and it is written down in this file.

Once a PIN is set, **changing it needs the current one**, so a child cannot
change the numbers that fence them in even if they got to the machine first.

**If you forget it**, or if your child set it before you got there, open a
terminal on your own account (the `parent` account, not the child's) and run:

```
sudo kidnix-set-pin --reset
```

It asks for **your** password and then for the new PIN, twice. Nothing your
child has made is touched.

The gate is a *usability* boundary: it stops a child wandering into settings.
It is not a safe. It cannot stop someone determined and older, and **the disk
is not encrypted**.

## How to change any of this

Everything below — how long a sitting is, how many children there are, which
pictures they see, how loud it is — is one app on **your** desktop, not a file
you have to find.

Log in as `parent` (the grown-up account, not your child's screen) and open
**Parent Panel** from the applications list. It has six pages:

* **Children** — add your children, one at a time, each with their own name,
  their own colour and shape, and their own age. Each one gets their own face
  on the first screen, their own drawings and their own daily total. Removing a
  child takes their face away and **keeps everything they made**.
* **Time** — how long one sitting lasts, how many minutes there are in a day,
  when bedtime starts, and how long the ending takes.
* **Activities** — which pictures your child sees, one tick-box each, with a
  line saying what each one is actually for. The first switch on the page is
  **"Keep the grid the same"**: leave it on and nothing new ever appears on
  your child's screen without you.
* **Sound & calm** — the volume, a silence switch, whether every spoken line is
  also written on the screen, and one **Calm mode** switch that slows the whole
  thing down for a hard day.
* **Their things** — copy your child's drawings out to a folder or a USB stick,
  open them, print one, or delete everything.
* **Updates & safety** — change the grown-up PIN, check for an update, and read
  in plain English what this machine does and does not send.

Change what you like across the pages, then press **Apply** once. It asks for
**your** password (not your child's PIN), and then it says:

> Saved. It takes effect at your child's next session.

That is exactly true: your child's screen reads these settings when a session
*starts*, so if they are using the computer right now, your change reaches them
the next time they switch it on.

**If something is wrong** — a bedtime that is not a time, a sitting shorter
than the ending that goes inside it — the panel says so in a sentence at the
top and will not let you save it. It is not being fussy; a settings file the
child's screen cannot read is a child's screen that does not start.

**If you would rather use a text editor**, you still can: the settings are
`/etc/kidnix/parent.toml` and `/etc/kidnix/session.toml`, they are ordinary
readable text, and the panel reads whatever it finds there the next time it
opens. The long explanation of what every setting means and why the numbers are
what they are lives in the copy the machine ships,
`/usr/share/kidnix/parent.toml`, which is replaced by every update so it never
goes out of date.

## Where the drawings are, and how to get one out

They live in your child's own account on the machine, which nothing else can
read — including your account. That is on purpose, and it is why there is a
command to fetch them.

Open a terminal on the parent account and run:

```
kidnix-export
```

It asks for **your** password (not the child's PIN) and makes one file in your
home folder called something like `kidnix-kid-2026-08-23-1430.tar.gz`. It has
everything in it: the drawings, the journal of what they did, everything.

To put it on a USB stick instead, plug the stick in and give it the path:

```
kidnix-export /run/media/parent/MY-USB
```

To open the file afterwards, double-click it, or:

```
tar -xzf kidnix-kid-2026-08-23-1430.tar.gz
```

The drawings are the `.png` files inside `.tuxpaint/saved/` and `Pictures/`.
Those you can print, or email to their grandmother, like any other picture.

**There is no backup.** Nothing copies these anywhere. If the laptop dies, they
are gone. Run `kidnix-export` onto a USB stick now and then.

## Giving the machine away, or starting again

```
kidnix-wipe
```

It lists exactly what it is about to delete, and will not do anything until you
type `DELETE`. It removes everything your child has made and every record of
what they did, and leaves the machine as it was on the first day. It does not
touch the accounts.

Run `kidnix-export` first if you want to keep any of it.

If you are handing the laptop to someone else, also change the grown-up PIN and
your own account password. **The disk is not encrypted.** Anyone who takes the
laptop apart can read what is on it. If that matters to you, do not put anything
on this machine you would mind losing with the machine.

## What the machine does and does not send

* **Your child's session cannot reach the internet at all.** Not "filtered", not
  "blocked by a list that might have a hole in it" — the firewall refuses every
  outgoing connection made by your child's account, by account, at the kernel.
  There is no browser on the machine for it to use even if it could.
* **Nothing is sent about your child. Ever.** No accounts, no analytics, no
  "usage data", no crash reports, no adverts. The activities are all offline
  programs; their sounds and pictures are already on the disk.
* **The machine itself** talks to the internet only when you ask it to — to fetch
  an update, or the one first-time download that installs the Scratch-like
  activity. Nothing is scheduled, nothing runs overnight.
* **What is written down about your child stays on the laptop**: their drawings,
  and a journal of what they opened and when, which is what the grown-up screen
  shows you. The system log keeps at most 30 days and no more than 200 MB.
* **Research recording is off.** kidnix has instrumentation in it for studying
  how children use it. It ships switched off, in `/etc/kidnix/research.toml`,
  and it stays off unless somebody deliberately turns it on.

**How you can check the first claim yourself**, without trusting us: while your
child's session is running, open a terminal on your own account and run
`sudo journalctl -u kidnix-egress` — you will see the rule that refuses their
account's traffic. Or simpler: there is no browser to open, and no activity on
the machine has anywhere to type an address.

## Updating it

kidnix does not update itself. Nothing happens on a timer, nothing reboots
overnight, and nothing changes under your child without you.

Right now updating means a grown-up running a command on the machine. There is
no button yet — that is deliberate: a one-tap update from the internet is only
safe once the machine checks who signed it, and that check is being finished
first. If you want it, ask; the person who builds your image can do it for you.

## If it will not start

1. **A blank or grey screen for more than a minute.** Hold the power button for
   ten seconds, let it go, press it again. It will come back to the last version
   that worked.
2. **It starts but the child's screen is missing** — you get a grey desktop or a
   login box instead. That is the grown-up desktop. Log in as `parent`; nothing
   is broken and nothing is lost.
3. **It asks for a password you do not have.** Whoever installed it set one. If
   nobody set one, the parent account is locked and there is no way in without a
   rescue USB stick — this is the one thing that cannot be fixed from the sofa,
   so it is worth checking on day one that you can log in as `parent`.
4. **Anything else.** The laptop is a laptop. Nothing on it is precious except
   the drawings, and `kidnix-export` is how you rescue those.

## Things people reasonably expect that are not true

Worth saying plainly, because the tiles are short and short is easy to
misread:

* **It does not teach phonics.** The letter activities play the letter's *name*
  ("ay", "bee", "see"), not the sound it makes in a word. English schools teach
  the sounds first. Use these for the alphabet, not for reading.
* **It is not a curriculum.** The eighteen picked activities in "Letters and
  numbers" touch a handful of the Early Years goals, not all of them. There is a
  full list with reasons on the machine itself at
  `/usr/share/kidnix/gcompris/CURATION.md`.
* **Drawing on a screen is not handwriting practice.** It is drawing. It is good
  for other reasons.
* **"Library" is empty** until a grown-up puts something in it. If you have not,
  the tile is not there at all — which is deliberate; a button that opens nothing
  is worse than no button.
* **25 minutes is a precaution, not a scientific threshold.** Nobody knows the
  right number. It is short on purpose and you can change it.

## Why it is the way it is

Three findings did most of the shaping, and they are worth one sentence each:

* Children of this age do not distinguish an advert from the thing they came
  for, so there are none, anywhere, of any kind.
* A young child's ability to stop an activity themselves is genuinely limited —
  which is why the ending is the computer's job and arrives the same way every
  time, rather than being a decision your child has to make.
* Sound and speech carry the instructions, because a four-year-old who cannot
  read still needs to be told what to do, and a picture alone does not do it.

---

*Costs, honestly: this needs its own laptop — it takes the whole machine over
and installing it erases everything already on the disk. A refurbished one is
around £150. It does not need a fast one.*
