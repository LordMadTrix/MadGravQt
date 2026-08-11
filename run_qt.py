#!/usr/bin/env python
"""Thin launcher for the wx-free MadGrav Qt6 shell.

Reuses the madgrav backend package installed editable from D:\\meerk40t
(same kernel, device drivers, geometry engine) -- see madgrav.py in that
repo for the original equivalent. wxPython is intentionally not
installed in this project's .venv, so madgrav/gui/plugin.py's own
ImportError handling disables the entire wx subsystem with no source
changes needed; -Z is passed as well as a belt-and-suspenders flag.
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
