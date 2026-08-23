#!/usr/bin/env python3
"""A chatroom for the expert-review panel, stored as append-only JSONL.

One JSON object per line:
  {"id": 17, "ts": "2026-08-23T10:12:03Z", "from": "cci-researcher",
   "to": "all", "re": 12, "text": "..."}

Usage:
  forum.py post --from <name> [--to <name>|all] [--re <id>] "<text>"
  forum.py read [--since <id>] [--from <name>] [--to <name>]
  forum.py tail [N]

Appends are single O_APPEND writes under a lock file, so concurrent posters
from different processes cannot interleave. The file is committed to the repo
as the record of the discussion.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import sys
from pathlib import Path

FORUM = Path(__file__).with_name("2026-08-23-forum.jsonl")
LOCK = FORUM.with_suffix(".lock")


def _load() -> list[dict]:
    if not FORUM.exists():
        return []
    out = []
    for line in FORUM.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def post(sender: str, text: str, to: str = "all", re: int | None = None) -> dict:
    with open(LOCK, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        msgs = _load()
        msg = {
            "id": (msgs[-1]["id"] + 1) if msgs else 1,
            "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "from": sender,
            "to": to,
            "re": re,
            "text": text,
        }
        with open(FORUM, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    return msg


def fmt(m: dict) -> str:
    re = f" (re #{m['re']})" if m.get("re") else ""
    to = "" if m.get("to", "all") == "all" else f" → {m['to']}"
    return f"#{m['id']} [{m['ts']}] {m['from']}{to}{re}:\n{m['text']}\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="forum.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("post")
    sp.add_argument("--from", dest="sender", required=True)
    sp.add_argument("--to", default="all")
    sp.add_argument("--re", type=int, default=None)
    sp.add_argument("text")
    sr = sub.add_parser("read")
    sr.add_argument("--since", type=int, default=0)
    sr.add_argument("--from", dest="sender", default=None)
    sr.add_argument("--to", default=None)
    st = sub.add_parser("tail")
    st.add_argument("n", nargs="?", type=int, default=10)
    a = p.parse_args(argv)

    if a.cmd == "post":
        m = post(a.sender, a.text, a.to, a.re)
        print(f"posted #{m['id']}")
        return 0
    msgs = _load()
    if a.cmd == "tail":
        msgs = msgs[-a.n :]
    else:
        msgs = [m for m in msgs if m["id"] > a.since]
        if a.sender:
            msgs = [m for m in msgs if m["from"] == a.sender]
        if a.to:
            msgs = [m for m in msgs if m.get("to") in (a.to, "all")]
    for m in msgs:
        print(fmt(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
