#!/usr/bin/env python
"""Thin launcher for the modern MadGrav Qt6 shell.

Starts the MadGrav Qt application with native Qt6 graphical interface.
"""

import re
import sys

from madgrav import main

if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    if "--qt" not in sys.argv:
        sys.argv.append("--qt")
    if "-Z" not in sys.argv and "--gui-suppress" not in sys.argv:
        sys.argv.append("-Z")
    sys.exit(main.run())
