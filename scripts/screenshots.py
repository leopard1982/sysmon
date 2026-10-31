#!/usr/bin/env python3
"""Buat screenshot untuk README (docs/screenshots/*.png) tanpa layar nyata.

Widget dirender offscreen di atas wallpaper buatan. Supaya tidak membocorkan data
pribadi (nama WiFi dsb.) dan grafiknya tidak datar, riwayat grafik, container Docker,
dan SSID diisi data DEMO. Sisanya (CPU, RAM, sensor, layanan) dibaca dari mesin ini.
"""
import math
import os
import random
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["HOME"] = tempfile.mkdtemp(prefix="sysmon-shot-")   # jangan pakai config user
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QRadialGradient  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import htop_widget as h  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots")
MARGIN = 48


def wallpaper(w, hgt):
    pm = QPixmap(w, hgt)
    g = QLinearGradient(0, 0, w, hgt)
    g.setColorAt(0, QColor("#0f2027"))
    g.setColorAt(0.5, QColor("#203a43"))
    g.setColorAt(1, QColor("#2c5364"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.fillRect(pm.rect(), g)
    for cx, cy, r, col in ((0.15, 0.2, 0.45, "#7e57c2"), (0.85, 0.8, 0.5, "#26a69a"), (0.6, 0.1, 0.3, "#ef5350")):
        rg = QRadialGradient(cx * w, cy * hgt, r * w)
        c = QColor(col)
        c.setAlpha(90)
        rg.setColorAt(0, c)
        c.setAlpha(0)
        rg.setColorAt(1, c)
        p.fillRect(pm.rect(), rg)
    p.end()
    return pm


def compose(widget, path):
    img = widget.grab().toImage()
    pm = wallpaper(img.width() + 2 * MARGIN, img.height() + 2 * MARGIN)
    p = QPainter(pm)
    p.drawImage(MARGIN, MARGIN, img)
    p.end()
    pm.save(path)
    print("tulis", os.path.relpath(path, ROOT))


def series(seed, base, amp, n=h.HISTORY):
    rnd = random.Random(seed)
    return [max(0, min(100, base + amp * math.sin(i / 5 + seed) + rnd.uniform(-amp / 2, amp / 2))) for i in range(n)]


def demo_data(w):
    for i, hist in enumerate(w.cpu_hist):
        hist.clear()
        hist.extend(series(i + 1, (18, 35, 12, 55)[i], 14))
    w.cpu_now = [hist[-1] for hist in w.cpu_hist]
    w.ram_hist.clear()
    w.ram_hist.extend(series(9, 46, 5))
    w.net_down.clear()
    w.net_down.extend(v * 40_000 for v in series(5, 50, 35))
    w.net_up.clear()
    w.net_up.extend(v * 6_000 for v in series(7, 40, 30))
    w.net_rate = (w.net_down[-1], w.net_up[-1])


def inject_poller(w):
    d = dict(w.poller.data)
    d["WiFi"] = {"ssid": "Home-WiFi", "signal": 78}
    w.smart.data = {   # DEMO: nilai contoh SMART NVMe
        "passed": True, "crit": 0, "spare": 100, "spare_thr": 1, "used": 2, "read": 9_300_000_000_000,
        "written": 16_600_000_000_000, "hours": 7516, "cycles": 298, "unsafe": 101, "media": 0,
        "model": "Samsung SSD 980 PRO 500GB", "fw": "5B2QGXA7",
    }
    if "Docker" in d and "error" not in d["Docker"]:
        d["Docker"] = {
            "version": d["Docker"]["version"],
            "containers": [
                {"Names": ["/web"], "State": "running", "Status": "Up 3 hours", "ImageID": "a"},
                {"Names": ["/api"], "State": "running", "Status": "Up 3 hours (healthy)", "ImageID": "b"},
                {"Names": ["/worker"], "State": "restarting", "Status": "Restarting (1) 5 seconds ago", "ImageID": "b"},
                {"Names": ["/migrate"], "State": "exited", "Status": "Exited (1) 2 hours ago", "ImageID": "c"},
            ],
            "images": [
                {"RepoTags": ["postgres:17"], "Size": 454_000_000, "Id": "d"},
                {"RepoTags": ["node:22"], "Size": 1_120_000_000, "Id": "b"},
                {"RepoTags": ["nginx:alpine"], "Size": 62_000_000, "Id": "a"},
            ],
            "used": {"a", "b"},
        }
    w.poller.data = d


def dashboard_shots(w, app):
    """Dashboard: riwayat layanan dan I/O NVMe diisi data DEMO supaya grafiknya tidak kosong."""
    rnd = random.Random(3)
    for name in ("PostgreSQL", "MariaDB", "MongoDB", "Redis", "Nginx", "Apache", "Internet", "UFW"):
        hist = w.svc_hist.setdefault(name, h.deque(maxlen=h.HISTORY))
        hist.clear()
        hist.extend((rnd.random() > 0.03, rnd.uniform(1, 25)) for _ in range(h.HISTORY))
    for q, top in ((w.nvme_r, 3e7), (w.nvme_w, 1e7)):
        q.clear()
        q.extend(rnd.uniform(0, top) for _ in range(h.HISTORY))
    dash = h.Dashboard(w)
    dash.show()
    for key, out in (("overview", "dashboard"), ("nvme", "dashboard-nvme"), ("PostgreSQL", "dashboard-service")):
        dash.tabs.setCurrentIndex([k for k, _ in dash.tab_keys].index(key))
        dash.refresh()
        app.processEvents()
        dash.grab().save(os.path.join(OUT, out + ".png"))
        print("tulis docs/screenshots/" + out + ".png")
    dash.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication(sys.argv)
    w = h.Widget()
    deadline = time.time() + 15
    while "Docker" not in w.poller.data and time.time() < deadline:
        time.sleep(0.3)
    for _ in range(3):
        w.tick()
        time.sleep(0.4)
    w.timer.stop()   # jangan tambah sampel nyata setelah data demo diisi
    demo_data(w)
    inject_poller(w)
    app.processEvents()

    h.LANG = "id"
    compose(w, os.path.join(OUT, "overview.png"))

    w.set_lang("en")
    inject_poller(w)
    compose(w, os.path.join(OUT, "overview-en.png"))
    w.set_lang("id")
    inject_poller(w)

    w.set_show_bg(False)
    inject_poller(w)
    compose(w, os.path.join(OUT, "no-background.png"))

    w.set_show_bg(True)
    w.set_theme("Hijau (Matrix)")
    w.set_font("Monospace")
    inject_poller(w)
    compose(w, os.path.join(OUT, "theme-matrix.png"))

    w.set_theme("Terang")
    w.set_font("Sans")
    inject_poller(w)
    compose(w, os.path.join(OUT, "theme-light.png"))

    w.set_theme("Default")
    inject_poller(w)
    dashboard_shots(w, app)

    h.make_icon(256).pixmap(256, 256).save(os.path.join(ROOT, "docs", "logo.png"))


if __name__ == "__main__":
    main()
