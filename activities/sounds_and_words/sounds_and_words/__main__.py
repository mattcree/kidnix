"""``python -m sounds_and_words`` -- the same entry point as the console script.

The manifest execs ``kidnix-sounds-and-words``; this is here so a developer can
run the activity out of a checkout without installing it, which is what
``just broadway`` does.
"""

from __future__ import annotations

import sys

from .activity import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
