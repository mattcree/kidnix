"""``python3 -m kidnix_parent_panel``. The same entry point as the console script."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
