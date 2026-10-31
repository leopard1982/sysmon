#!/usr/bin/env python3
"""Render ikon PNG (berbagai ukuran) dari make_icon() ke pohon paket Debian.

Pemakaian: make_icons.py <stage_dir> [logo_out.png]
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PyQt5.QtWidgets import QApplication  # noqa: E402

import htop_widget as h  # noqa: E402

SIZES = (16, 22, 24, 32, 48, 64, 128, 256)


def main():
    stage = sys.argv[1]
    app = QApplication(["make_icons"])  # noqa: F841
    for n in SIZES:
        d = os.path.join(stage, f"usr/share/icons/hicolor/{n}x{n}/apps")
        os.makedirs(d, exist_ok=True)
        h.make_icon(n).pixmap(n, n).save(os.path.join(d, "desktop-htop.png"))
    pix = os.path.join(stage, "usr/share/pixmaps")
    os.makedirs(pix, exist_ok=True)
    h.make_icon(64).pixmap(64, 64).save(os.path.join(pix, "desktop-htop.png"))
    if len(sys.argv) > 2:
        h.make_icon(256).pixmap(256, 256).save(sys.argv[2])


if __name__ == "__main__":
    main()
