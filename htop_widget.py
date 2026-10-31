#!/usr/bin/env python3
"""System Monitoring: widget desktop untuk CPU (per core), RAM, swap, PostgreSQL, MariaDB, NVMe, dan sensors.

Interaksi:
  - Drag kiri      : pindahkan widget (posisi tersimpan)
  - Warna          : hijau = bagus, kuning = hati-hati, merah = tinggi
  - Klik kanan     : menu (kunci posisi, transparansi, keluar)
"""
import glob
import http.client
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
from calendar import monthrange
from collections import deque
from datetime import datetime

import psutil
from PyQt5.QtCore import QDir, QLockFile, QPointF, QPropertyAnimation, QRectF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QImage, QLinearGradient, QRadialGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QInputDialog, QMenu, QSystemTrayIcon, QWidget

CONFIG = os.path.expanduser("~/.config/desktop_htop.json")
HISTORY = 60          # jumlah sampel grafik
INTERVALS = ((1, "iv1"), (5, "iv5"), (30, "iv30"), (60, "iv60"))   # (detik, kunci terjemahan)
APP_NAME = "System Monitoring"
COLW = 296
W, H = 16 + 4 * COLW + 3 * 24 + 16, 660
W2 = 16 + 3 * COLW + 2 * 24 + 16   # lebar tanpa kolom Docker
DOCKER_SOCK = "/var/run/docker.sock"
DOCKER_MAX_ROWS = 10
NVME_DEV = "nvme0n1"
NVME_CTRL = "nvme0"
MIN_SERVICE_INTERVAL = 3  # detik

ACCENT = QColor("#4fc3f7")
OK = QColor("#81c784")
WARN = QColor("#ffeb3b")
CRIT = QColor("#e57373")
TEXT = QColor("#eceff1")
MUTED = QColor("#90a4ae")
UPLOAD = QColor("#ba68c8")
SHADOW = QColor(0, 0, 0, 200)

# Tema: warna background (atas, bawah) + warna teks/judul/grafik yang serasi dengannya.
# Warna status (hijau/kuning/merah) tetap, kecuali tema terang yang memakai versi lebih gelap.
THEMES = {
    "Default":        dict(bg=("#1e2838", "#080c14"), text="#eceff1", muted="#90a4ae", accent="#4fc3f7", upload="#ba68c8", shadow="#000000"),
    "Hitam":          dict(bg=("#161616", "#000000"), text="#f5f5f5", muted="#9e9e9e", accent="#b0bec5", upload="#ce93d8", shadow="#000000"),
    "Biru":           dict(bg=("#16325c", "#060f24"), text="#e3f2fd", muted="#8fb3d9", accent="#64b5f6", upload="#f48fb1", shadow="#000000"),
    "Hijau (Matrix)": dict(bg=("#0c2a1c", "#020a06"), text="#b9f6ca", muted="#69a77f", accent="#00e676", upload="#76ff03", shadow="#000000"),
    "Amber":          dict(bg=("#33210a", "#0e0802"), text="#ffe0b2", muted="#bf9b6b", accent="#ffab40", upload="#ff7043", shadow="#000000"),
    "Ungu":           dict(bg=("#32204f", "#0f0820"), text="#f3e5f5", muted="#b39ddb", accent="#ce93d8", upload="#80d8ff", shadow="#000000"),
    "Merah":          dict(bg=("#4a1a1f", "#1a080b"), text="#ffebee", muted="#c99aa0", accent="#ff8a80", upload="#ffd180", shadow="#000000"),
    "Terang":         dict(bg=("#f5f7fa", "#cfd8dc"), text="#102027", muted="#455a64", accent="#01579b", upload="#6a1b9a", shadow="#ffffff",
                           ok="#2e7d32", warn="#e65100", crit="#c62828", light=True),
}
THEME_ALIAS = {"Gelap": "Terang", "Putih": "Default"}   # nama dari versi lama
BG_TOP, BG_BOTTOM = QColor("#1e2838"), QColor("#080c14")
TRACK = QColor("#ffffff")   # warna lapisan tipis (jalur grafik/bar, garis); hitam di tema terang
FONTS = {"Sans": "Sans", "Monospace": "Monospace", "Serif": "Serif"}
FONT_FAMILY = "Sans"
FX = True   # efek visual: glow, gradasi


# ---------- bahasa ----------
LANGS = {"id": "Bahasa Indonesia", "en": "English"}
LANG = "id"

I18N = {
    # menu
    "menu.toggle": ("Tampilkan / sembunyikan widget", "Show / hide widget"),
    "menu.lock": ("Kunci posisi", "Lock position"),
    "menu.top": ("Tampilkan di atas (selalu di depan)", "Show on top (always in front)"),
    "menu.bg": ("Tampilkan background", "Show background"),
    "menu.opacity": ("Transparansi background", "Background opacity"),
    "op.light": ("Tipis", "Light"),
    "op.medium": ("Sedang", "Medium"),
    "op.solid": ("Pekat", "Solid"),
    "menu.services": ("Layanan monitoring", "Monitored services"),
    "menu.show": ("Tampilkan", "Show"),
    "menu.port": ("Port: {port} (ubah…)", "Port: {port} (change…)"),
    "menu.docker": ("Docker (tampilkan)", "Docker (show)"),
    "menu.fx": ("Efek visual (glow)", "Visual effects (glow)"),
    "menu.theme": ("Tema", "Theme"),
    "menu.font": ("Jenis font", "Font"),
    "menu.interval": ("Interval update", "Update interval"),
    "menu.lang": ("Bahasa / Language", "Language / Bahasa"),
    "menu.autostart": ("Jalankan otomatis saat login", "Start automatically at login"),
    "menu.quit": ("Keluar", "Quit"),
    "iv1": ("1 detik", "1 second"),
    "iv5": ("5 detik", "5 seconds"),
    "iv30": ("30 detik", "30 seconds"),
    "iv60": ("1 menit", "1 minute"),
    "dlg.port_title": ("Port {name}", "{name} port"),
    "dlg.port_label": ("Port {name} (1-65535):", "{name} port (1-65535):"),
    # judul section
    "sec.memory": ("MEMORI", "MEMORY"),
    "sec.network": ("JARINGAN", "NETWORK"),
    "sec.services": ("LAYANAN", "SERVICES"),
    "sec.sensors": ("SENSOR", "SENSORS"),
    "sec.containers": ("CONTAINER", "CONTAINERS"),
    "sec.images": ("IMAGE", "IMAGES"),
    "sec.battery": ("BATERAI", "BATTERY"),
    "sec.system": ("SISTEM", "SYSTEM"),
    "sec.smart": ("SMART NVMe", "NVMe SMART"),
    # isi
    "checking": ("memeriksa…", "checking…"),
    "mem.avail": ("tersedia {size}", "available {size}"),
    "swap.off": ("swap tidak aktif", "swap is off"),
    "net.noconn": ("tidak ada koneksi", "no connection"),
    "net.offline": ("offline", "offline"),
    "net.online": ("online · {ms} ms", "online · {ms} ms"),
    "wifi.signal": ("sinyal {sig}%", "signal {sig}%"),
    "wifi.disc": ("tidak terhubung", "not connected"),
    "dk.denied": ("akses ditolak (butuh grup docker)", "permission denied (needs docker group)"),
    "dk.inactive": ("docker tidak aktif", "docker is not running"),
    "dk.summary": ("{n} / {t} aktif · v{v}", "{n} / {t} running · v{v}"),
    "dk.nocont": ("tidak ada container", "no containers"),
    "dk.noimg": ("tidak ada image", "no images"),
    "dk.images": ("{n} image · {size}", "{n} images · {size}"),
    "more": ("+{n} lainnya", "+{n} more"),
    "svc.none": ("tidak ada layanan ditampilkan", "no services shown"),
    "svc.running": ("berjalan", "running"),
    "svc.down": ("mati", "down"),
    "svc.noresp": ("tidak merespons", "not responding"),
    "nvme.temp": ("Suhu", "Temp"),
    "sensors.none": ("sensor tidak terdeteksi", "no sensors detected"),
    "bat.full": ("penuh", "full"),
    "bat.cap": ("Kapasitas", "Charge"),
    "bat.health": ("Kesehatan", "Health"),
    "bat.cycles": ("Siklus", "Cycles"),
    "bat.power": ("Daya", "Power"),
    "ufw.active": ("aktif", "active"),
    "ufw.inactive": ("nonaktif", "inactive"),
    "ufw.policy": ("masuk {i} · keluar {o}", "in {i} · out {o}"),
    "ufw.rules": (" · {n} aturan", " · {n} rules"),
    "smart.missing": ("smartctl belum terpasang", "smartctl is not installed"),
    "smart.missing.hint": ("sudo apt install smartmontools", "sudo apt install smartmontools"),
    "smart.denied": ("butuh izin root untuk membaca SMART", "root access needed to read SMART"),
    "smart.denied.hint": ("sudo desktop-htop-smart-setup", "sudo desktop-htop-smart-setup"),
    "smart.fail": ("gagal membaca SMART", "could not read SMART"),
    "smart.health": ("Kesehatan", "Health"),
    "smart.spare": ("Cadangan", "Spare"),
    "smart.wear": ("Keausan", "Wear"),
    "smart.rw": ("Tulis / baca", "Write / read"),
    "smart.poh": ("Waktu nyala", "Power on"),
    "smart.poh.val": ("{h} jam · {d} hari", "{h} h · {d} d"),
    "smart.cyc": ("Nyala · mati paksa", "Cycles · unsafe"),
    "smart.media": ("Error media", "Media errors"),
    "nvme.model": ("Model", "Model"),
    "sys.age": ("Usia instalasi", "Install age"),
    "sys.since": ("sejak {date}", "since {date}"),
    "sys.unknown": ("tidak diketahui", "unknown"),
    "age.y": ("{n} thn", "{n} yr"),
    "age.m": ("{n} bln", "{n} mo"),
    "age.d": ("{n} hr", "{n} d"),
    "age.h": ("{n} jam", "{n} h"),
    "bat.charging": ("mengisi daya", "charging"),
    "bat.discharging": ("memakai baterai", "discharging"),
    "legend.ok": ("Bagus", "Good"),
    "legend.warn": ("Hati-hati", "Caution"),
    "legend.crit": ("Tinggi", "High"),
}

THEME_EN = {"Hitam": "Black", "Biru": "Blue", "Hijau (Matrix)": "Green (Matrix)", "Ungu": "Purple",
            "Merah": "Red", "Terang": "Light"}


def tr(key, **kw):
    text = I18N[key][0 if LANG == "id" else 1]
    return text.format(**kw) if kw else text


def theme_label(name):
    return THEME_EN.get(name, name) if LANG == "en" else name


def detect_lang():
    loc = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    return "id" if loc.lower().startswith("id") else "en"


def apply_theme(name):
    global TEXT, MUTED, ACCENT, UPLOAD, SHADOW, OK, WARN, CRIT, BG_TOP, BG_BOTTOM, TRACK
    t = THEMES.get(name, THEMES["Default"])
    OK, WARN, CRIT = (QColor(t.get(k, d)) for k, d in (("ok", "#81c784"), ("warn", "#ffeb3b"), ("crit", "#e57373")))
    TEXT, MUTED, ACCENT, UPLOAD = (QColor(t[k]) for k in ("text", "muted", "accent", "upload"))
    BG_TOP, BG_BOTTOM = (QColor(c) for c in t["bg"])
    TRACK = QColor("#000000" if t.get("light") else "#ffffff")
    SHADOW = QColor(t["shadow"])
    SHADOW.setAlpha(200)


def alpha(color, a):
    c = QColor(color)
    c.setAlpha(a)
    return c


def glow_dot(p, cx, cy, r, color):
    """Titik indikator dengan halo lembut."""
    p.setPen(Qt.NoPen)
    if FX:
        halo = QRadialGradient(cx, cy, r * 3.2)
        halo.setColorAt(0, alpha(color, 120))
        halo.setColorAt(1, alpha(color, 0))
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(cx, cy), r * 3.2, r * 3.2)
    p.setBrush(color)
    p.drawEllipse(QPointF(cx, cy), r, r)


def font(size, weight=QFont.Normal):
    return QFont(FONT_FAMILY, size, weight)


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        with open(CONFIG, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def level_color(pct):
    if pct >= 85:
        return CRIT
    if pct >= 60:
        return WARN
    return OK


def temp_color(t, high):
    ratio = t / high if high else t / 100
    return CRIT if ratio >= 0.9 else WARN if ratio >= 0.7 else OK


def fmt_bytes(n):
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.0f} MB"
    return f"{n / 1024 ** 3:.1f} GB"


def probe_postgres(host="127.0.0.1", port=5432):
    """Kirim SSLRequest; server PostgreSQL membalas 'S' atau 'N' (tanpa kredensial)."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=1) as c:
            c.settimeout(1)
            c.sendall(b"\x00\x00\x00\x08\x04\xd2\x16\x2f")
            ok = c.recv(1) in (b"S", b"N")
    except OSError:
        return {"up": False}
    return {"up": ok, "ms": (time.monotonic() - t0) * 1000, "version": f"port {port}"}


def probe_mariadb(host="127.0.0.1", port=3306):
    """Baca handshake greeting MariaDB/MySQL (berisi versi server, tanpa kredensial)."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=1) as c:
            c.settimeout(1)
            data = c.recv(256)
    except OSError:
        return {"up": False}
    ms = (time.monotonic() - t0) * 1000
    version = f"port {port}"
    if len(data) > 5 and data[4] == 10:
        version = data[5:].split(b"\0")[0].decode(errors="replace")
        if version.startswith("5.5.5-"):
            version = version[6:]
        version = version.split()[0].split("-0+")[0]
    return {"up": len(data) > 4, "ms": ms, "version": version}


def _bson_cmd(cmd):
    body = (b"\x10" + cmd.encode() + b"\0" + struct.pack("<i", 1)
            + b"\x02$db\0" + struct.pack("<i", 6) + b"admin\0" + b"\0")
    return struct.pack("<i", len(body) + 4) + body


def probe_mongodb(host="127.0.0.1", port=27017):
    """Kirim buildInfo (OP_MSG) ke MongoDB; perintah ini boleh tanpa autentikasi."""
    msg = struct.pack("<I", 0) + b"\x00" + _bson_cmd("buildInfo")
    pkt = struct.pack("<iiii", 16 + len(msg), 1, 0, 2013) + msg
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=1) as c:
            c.settimeout(1)
            ms = (time.monotonic() - t0) * 1000
            c.sendall(pkt)
            data = c.recv(65536)
            if len(data) >= 4:
                want = struct.unpack("<i", data[:4])[0]
                while len(data) < want:
                    chunk = c.recv(65536)
                    if not chunk:
                        break
                    data += chunk
    except OSError:
        return {"up": False}
    version = f"port {port}"
    i = data.find(b"\x02version\x00")
    if i >= 0:
        n = struct.unpack("<i", data[i + 9:i + 13])[0]
        version = "v" + data[i + 13:i + 13 + n - 1].decode(errors="replace")
    return {"up": True, "ms": ms, "version": version}


def probe_redis(host="127.0.0.1", port=6379):
    """PING lalu INFO server (inline protocol). -NOAUTH tetap berarti server hidup."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=1) as c:
            c.settimeout(1)
            c.sendall(b"PING\r\n")
            reply = c.recv(256)
            ms = (time.monotonic() - t0) * 1000
            version = f"port {port}"
            if reply.startswith(b"+PONG"):
                c.sendall(b"INFO server\r\n")
                info = b""
                while b"redis_version:" not in info or not info.endswith(b"\r\n"):
                    chunk = c.recv(4096)
                    if not chunk:
                        break
                    info += chunk
                    if len(info) > 16384:
                        break
                m = re.search(rb"redis_version:([^\r\n]+)", info)
                if m:
                    version = "v" + m.group(1).decode(errors="replace")
            elif reply.startswith((b"-NOAUTH", b"-DENIED")):
                version = "auth required"
            elif not reply.startswith(b"-"):
                return {"up": False}
    except OSError:
        return {"up": False}
    return {"up": True, "ms": ms, "version": version}


def probe_web(port, pattern, host="127.0.0.1"):
    """HEAD / ke web server lokal; versi dibaca dari header Server (kalau tidak disembunyikan)."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=1) as c:
            c.settimeout(1)
            c.sendall(b"HEAD / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            data = c.recv(2048)
    except OSError:
        return {"up": False}
    ms = (time.monotonic() - t0) * 1000
    if not data.startswith(b"HTTP/"):
        return {"up": False}
    m = re.search(pattern, data, re.I)
    return {"up": True, "ms": ms, "version": "v" + m.group(1).decode() if m else f"port {port}"}


def probe_nginx(port=80):
    return probe_web(port, rb"Server:\s*nginx/([\d.]+)")


def probe_apache(port=80):
    return probe_web(port, rb"Server:\s*Apache/([\d.]+)")


def probe_ufw(port=None):
    """Status UFW tanpa root: ENABLED di /etc/ufw/ufw.conf dan kebijakan bawaan di /etc/default/ufw."""
    if not any(os.path.exists(f) for f in ("/usr/sbin/ufw", "/etc/ufw")):
        return {"up": False, "absent": True}
    conf = read_sysfs("/etc/ufw/ufw.conf")
    m = re.search(r"^ENABLED=(\w+)", conf, re.M)
    if m:
        enabled = m.group(1).lower() == "yes"
    else:   # ufw.conf tidak terbaca: tanya systemd
        try:
            enabled = subprocess.run(["systemctl", "is-active", "--quiet", "ufw"], timeout=2).returncode == 0
        except (OSError, subprocess.SubprocessError):
            enabled = False
    default = read_sysfs("/etc/default/ufw")
    pol = {k: (re.search(rf'^DEFAULT_{k}_POLICY="?(\w+)', default, re.M) or [None, "?"])[1] for k in ("INPUT", "OUTPUT")}
    rules = read_sysfs("/etc/ufw/user.rules")   # biasanya hanya root yang boleh baca
    return {"up": enabled, "ms": 0, "up_key": "ufw.active", "down_key": "ufw.inactive",
            "policy": (pol["INPUT"], pol["OUTPUT"]),
            "rules": rules.count("### tuple ###") if rules else None}


class _UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path, timeout=2):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def docker_get(path):
    conn = _UnixHTTP(DOCKER_SOCK)
    try:
        conn.request("GET", path)
        return json.loads(conn.getresponse().read())
    finally:
        conn.close()


def read_docker():
    """Container dan image dari Docker Engine API lewat unix socket."""
    try:
        version = docker_get("/version")["Version"]
        containers = docker_get("/containers/json?all=1")
        images = docker_get("/images/json")
    except PermissionError:
        return {"error": "dk.denied"}
    except (OSError, ValueError, KeyError, http.client.HTTPException):
        return {"error": "dk.inactive"}
    used = {c["ImageID"] for c in containers if c.get("State") == "running"}
    return {"version": version, "containers": containers, "images": images, "used": used}


def probe_internet():
    """Cek koneksi internet lewat TCP ke DNS publik; ukur latensi."""
    for host in ("1.1.1.1", "8.8.8.8"):
        t0 = time.monotonic()
        try:
            socket.create_connection((host, 53), timeout=1.0).close()
            return {"up": True, "ms": (time.monotonic() - t0) * 1000}
        except OSError:
            continue
    return {"up": False}


def pick_iface():
    """Interface aktif: wifi dulu, kalau tidak ada ambil interface fisik pertama yang up."""
    try:
        stats = psutil.net_if_stats()
    except Exception:
        return None, False
    for n, st in stats.items():
        if st.isup and os.path.isdir(f"/sys/class/net/{n}/wireless"):
            return n, True
    for n, st in stats.items():
        if st.isup and n != "lo" and not n.startswith(("docker", "br-", "veth", "virbr")):
            return n, False
    return None, False


def read_wifi():
    """SSID dan kekuatan sinyal (%) jaringan wifi aktif via nmcli."""
    try:
        out = subprocess.run(["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi"],
                             capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        if line.startswith("yes:"):
            body, _, signal = line[4:].rpartition(":")
            ssid = re.sub(r"\\(.)", r"\1", body)
            return {"ssid": ssid or "(hidden)", "signal": int(signal) if signal.isdigit() else None}
    return None


def fmt_rate(bps):
    if bps >= 1e6:
        return f"{bps / 1e6:.1f} MB/s"
    if bps >= 1e3:
        return f"{bps / 1e3:.0f} KB/s"
    return f"{bps:.0f} B/s"


def proc_stats(names):
    count = rss = 0
    for pr in psutil.process_iter(["name", "memory_info"]):
        try:
            if pr.info["name"] in names:
                count += 1
                rss += pr.info["memory_info"].rss
        except (psutil.Error, TypeError, AttributeError):
            pass
    return count, rss


# (nama, fungsi probe, nama proses, port bawaan)
SERVICES = (
    ("PostgreSQL", probe_postgres, {"postgres"}, 5432),
    ("MariaDB", probe_mariadb, {"mariadbd", "mysqld"}, 3306),
    ("MongoDB", probe_mongodb, {"mongod", "mongos"}, 27017),
    ("Redis", probe_redis, {"redis-server"}, 6379),
    ("Nginx", probe_nginx, {"nginx"}, 80),
    ("Apache", probe_apache, {"apache2", "httpd"}, 80),
    ("UFW", probe_ufw, set(), None),
)
# Layanan opsional: baris disembunyikan kalau tidak terpasang.
INSTALLED = {
    "Nginx": ("/usr/sbin/nginx", "/etc/nginx"),
    "Apache": ("/usr/sbin/apache2", "/usr/sbin/httpd", "/etc/apache2", "/etc/httpd"),
}
PROC_REQUIRED = {"Nginx", "Apache"}   # port 80 bisa dipakai server lain, jadi proses harus ada


class ServicePoller(threading.Thread):
    """Cek service di thread terpisah supaya UI tidak tersendat. Hanya yang ditampilkan yang dicek."""

    def __init__(self):
        super().__init__(daemon=True)
        self.data = {}
        self.interval = MIN_SERVICE_INTERVAL
        self.config = {}                 # {nama: {"show": bool, "port": int}}, diisi widget
        self.wake = threading.Event()    # bangunkan poller saat setting berubah

    def run(self):
        while True:
            res = {}
            for key, probe, names, default_port in SERVICES:
                conf = self.config.get(key, {})
                if not conf.get("show", True):
                    continue
                if key in INSTALLED and not any(os.path.exists(f) for f in INSTALLED[key]):
                    res[key] = {"up": False, "absent": True}
                    continue
                info = probe(port=conf.get("port", default_port))
                info["procs"], info["rss"] = proc_stats(names) if names else (0, 0)
                if key in PROC_REQUIRED and not info["procs"]:
                    info["up"] = False
                res[key] = info
            if self.config.get("Docker", {}).get("show", True):
                res["Docker"] = read_docker()
            res["Internet"] = probe_internet()
            res["WiFi"] = read_wifi()
            self.data = res
            self.wake.wait(self.interval)
            self.wake.clear()


def read_swaps():
    """Daftar swap aktif dari /proc/swaps: (nama, tipe, total_bytes, used_bytes)."""
    rows = []
    try:
        with open("/proc/swaps") as f:
            next(f)
            for line in f:
                name, kind, size, used, _ = line.split()[:5]
                rows.append((name, kind, int(size) * 1024, int(used) * 1024))
    except (OSError, ValueError, StopIteration):
        pass
    return rows


def read_sysfs(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def read_nvme_info():
    base = f"/sys/class/nvme/{NVME_CTRL}"
    info = {
        "state": read_sysfs(f"{base}/state", "unknown"),
        "model": read_sysfs(f"{base}/model", NVME_DEV),
        "fw": read_sysfs(f"{base}/firmware_rev"),
        "temp": None, "high": None,
    }
    for hw in glob.glob(f"{base}/hwmon*"):
        t = read_sysfs(f"{hw}/temp1_input")
        if t.isdigit():
            info["temp"] = int(t) / 1000
            hi = read_sysfs(f"{hw}/temp1_max")
            info["high"] = int(hi) / 1000 if hi.isdigit() else None
            break
    return info


def find_smartctl():
    if os.access("/usr/sbin/smartctl", os.X_OK):
        return "/usr/sbin/smartctl"
    return shutil.which("smartctl", path=os.pathsep.join([os.environ.get("PATH", ""), "/usr/sbin", "/sbin", "/usr/local/sbin"]))


def read_smart():
    """SMART/Health NVMe lewat smartctl (JSON). Coba langsung, lalu `sudo -n` (lihat desktop-htop-smart-setup)."""
    exe = find_smartctl()
    if not exe:
        return {"error": "smart.missing"}
    dev = f"/dev/{NVME_CTRL}"
    if not os.path.exists(dev):
        return {"error": "smart.fail"}
    log = status = model = fw = None
    for cmd in ([exe], ["sudo", "-n", exe]):
        try:
            out = subprocess.run(cmd + ["-j", "-i", "-H", "-A", dev], capture_output=True, text=True,
                                 timeout=10, stdin=subprocess.DEVNULL).stdout
            d = json.loads(out)
        except (OSError, subprocess.SubprocessError, ValueError):
            continue
        if isinstance(d.get("nvme_smart_health_information_log"), dict):
            log, status = d["nvme_smart_health_information_log"], d.get("smart_status", {})
            model, fw = d.get("model_name"), d.get("firmware_version")
            break
    if log is None:
        return {"error": "smart.denied"}
    unit = 512_000   # 1 data unit NVMe = 1000 x 512 byte
    return {"passed": status.get("passed", True), "crit": log.get("critical_warning", 0),
            "spare": log.get("available_spare"), "spare_thr": log.get("available_spare_threshold"),
            "used": log.get("percentage_used"), "read": log.get("data_units_read", 0) * unit,
            "written": log.get("data_units_written", 0) * unit, "hours": log.get("power_on_hours"),
            "cycles": log.get("power_cycles"), "unsafe": log.get("unsafe_shutdowns"),
            "media": log.get("media_errors", 0), "model": model, "fw": fw}


class SmartPoller(threading.Thread):
    """SMART berubah pelan dan smartctl lambat: cek tiap 5 menit (1 menit selama masih gagal)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.data = None

    def run(self):
        while True:
            self.data = read_smart()
            time.sleep(60 if "error" in self.data else 300)


def read_battery():
    """Kondisi baterai dari sysfs: kapasitas, kesehatan (full / design), siklus, daya."""
    for base in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        def num(name):
            v = read_sysfs(f"{base}/{name}")
            return int(v) if v.lstrip("-").isdigit() else None
        energy = num("energy_full_design") is not None
        full, design = (num("energy_full"), num("energy_full_design")) if energy else (num("charge_full"), num("charge_full_design"))
        volt = num("voltage_min_design") or num("voltage_now")
        to_wh = (lambda v: v / 1e6) if energy else (lambda v: v * volt / 1e12 if volt else None)
        watts = None
        if energy and num("power_now"):
            watts = num("power_now") / 1e6
        elif num("current_now") and num("voltage_now"):
            watts = num("current_now") * num("voltage_now") / 1e12
        return {"name": os.path.basename(base), "capacity": num("capacity"), "status": read_sysfs(f"{base}/status"),
                "health": full / design * 100 if full and design else None,
                "full_wh": to_wh(full) if full else None, "design_wh": to_wh(design) if design else None,
                "cycles": num("cycle_count"), "model": read_sysfs(f"{base}/model_name"),
                "tech": read_sysfs(f"{base}/technology"), "watts": abs(watts) if watts else None}
    return None


def read_install_time():
    """Waktu Linux dipasang: pembuatan folder log installer, atau pembuatan filesystem root (birth time)."""
    for path in ("/var/log/installer", "/", "/lost+found", "/etc/machine-id"):
        try:
            out = subprocess.run(["stat", "-c", "%W", path], capture_output=True, text=True, timeout=2).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if out.isdigit() and int(out) > 0:
            return datetime.fromtimestamp(int(out))
    return None


def fmt_age(then, now=None):
    now = now or datetime.now()
    y, m, d = now.year - then.year, now.month - then.month, now.day - then.day
    if d < 0:
        m -= 1
        d += monthrange(now.year if now.month > 1 else now.year - 1, now.month - 1 or 12)[1]
    if m < 0:
        y, m = y - 1, m + 12
    if y:
        return " ".join([tr("age.y", n=y)] + ([tr("age.m", n=m)] if m else []))
    if m:
        return " ".join([tr("age.m", n=m)] + ([tr("age.d", n=d)] if d else []))
    if d:
        return tr("age.d", n=d)
    return tr("age.h", n=int((now - then).total_seconds() // 3600))


def read_os_name():
    m = re.search(r'^PRETTY_NAME="?([^"\n]+)', read_sysfs("/etc/os-release"), re.M)
    return m.group(1) if m else "Linux"


def fmt_tb(n):
    return f"{n / 1e12:.1f} TB" if n >= 1e12 else f"{n / 1e9:.0f} GB"


BOLT = ((38, 4), (14, 36), (28, 36), (22, 60), (50, 24), (35, 24), (44, 4))


def make_icon(size=64):
    """Ikon petir kuning di lingkaran merah (gaya The Flash); koordinat dasar 64x64."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 64, size / 64)
    p.setPen(QPen(QColor("#ffd600"), 3))
    p.setBrush(QColor("#d32f2f"))
    p.drawEllipse(QRectF(3, 3, 58, 58))
    bolt = QPainterPath()
    bolt.moveTo(*BOLT[0])
    for pt in BOLT[1:]:
        bolt.lineTo(*pt)
    bolt.closeSubpath()
    p.setPen(QPen(QColor("#fff59d"), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor("#ffeb3b"))
    p.drawPath(bolt)
    p.end()
    return QIcon(pm)


AUTOSTART_FILE = os.path.expanduser("~/.config/autostart/desktop-htop.desktop")
SYSTEM_AUTOSTART = "/etc/xdg/autostart/desktop-htop.desktop"


def autostart_enabled():
    """Berkas user menimpa berkas sistem; Hidden=true berarti dimatikan."""
    path = AUTOSTART_FILE if os.path.exists(AUTOSTART_FILE) else SYSTEM_AUTOSTART
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return False
    return "Hidden=true" not in text and "X-GNOME-Autostart-enabled=false" not in text


def set_autostart(on):
    lines = [
        "[Desktop Entry]", "Type=Application", f"Name={APP_NAME}", "Exec=desktop-htop",
        "Icon=desktop-htop", "Terminal=false",
        f"X-GNOME-Autostart-enabled={'true' if on else 'false'}",
        "X-GNOME-Autostart-Delay=3", "X-KDE-autostart-after=panel",
    ]
    if not on:
        lines.append("Hidden=true")
    try:
        os.makedirs(os.path.dirname(AUTOSTART_FILE), exist_ok=True)
        with open(AUTOSTART_FILE, "w") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


class Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.opacity_bg = self.cfg.get("opacity", 140)
        self.show_bg = self.cfg.get("show_bg", True)
        if self.opacity_bg == 0:            # migrasi: dulu "Transparan" = opacity 0
            self.opacity_bg, self.show_bg = 140, False
        self.locked = self.cfg.get("locked", False)
        self.on_top = bool(self.cfg.get("on_top", False))
        self.svc = {n: {"show": True, **({"port": port} if port else {})} for n, _, _, port in SERVICES}
        self.svc["Docker"] = {"show": True}
        for k, v in (self.cfg.get("services") or {}).items():
            if k in self.svc and isinstance(v, dict):
                if isinstance(v.get("show"), bool):
                    self.svc[k]["show"] = v["show"]
                if "port" in self.svc[k] and isinstance(v.get("port"), int) and 1 <= v["port"] <= 65535:
                    self.svc[k]["port"] = v["port"]
        global FX
        FX = self.cfg.get("fx", True)
        global LANG
        LANG = self.cfg.get("lang") if self.cfg.get("lang") in LANGS else detect_lang()
        self.theme = THEME_ALIAS.get(self.cfg.get("theme"), self.cfg.get("theme", "Default"))
        if self.theme not in THEMES:
            self.theme = "Default"
        global FONT_FAMILY
        FONT_FAMILY = FONTS.get(self.cfg.get("font"), "Sans")
        self.font_name = next(k for k, v in FONTS.items() if v == FONT_FAMILY)
        apply_theme(self.theme)
        self.interval = self.cfg.get("interval", 1)
        if self.interval not in dict(INTERVALS):
            self.interval = 1

        self.ncpu = psutil.cpu_count(logical=True) or 4
        self.cpu_hist = [deque([0] * HISTORY, maxlen=HISTORY) for _ in range(self.ncpu)]
        self.cpu_now = [0.0] * self.ncpu
        self.freq = None
        self.ram_hist = deque([0] * HISTORY, maxlen=HISTORY)
        self.mem = psutil.virtual_memory()
        self.swap = psutil.swap_memory()
        self.sensors = []   # (label, value_str, color)
        self.swaps = read_swaps()
        self.nvme = read_nvme_info()
        self.battery = read_battery()
        self.install_time = read_install_time()
        self.os_name = read_os_name()
        self.smart = SmartPoller()
        self.smart.start()
        self.nvme_parts = []
        self.nvme_io = None          # (read B/s, write B/s, busy %)
        self._io_prev = None
        self.iface, self.is_wifi = pick_iface()
        self.net_down = deque([0] * HISTORY, maxlen=HISTORY)
        self.net_up = deque([0] * HISTORY, maxlen=HISTORY)
        self.net_rate = (0.0, 0.0)
        self._net_prev = None
        self.poller = ServicePoller()
        self.poller.interval = max(MIN_SERVICE_INTERVAL, self.interval)
        self.poller.config = self.svc
        self.poller.start()
        self.drag = None

        self.setWindowFlags(self.window_flags())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_X11NetWmWindowTypeDesktop, False)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_icon())
        self.logo = make_icon(128).pixmap(128, 128)
        self.resize(self.desired_width(), H)
        self.move(self.cfg.get("x", 40), self.cfg.get("y", 60))

        psutil.cpu_percent(percpu=True)  # prime
        self.tick()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.interval * 1000)
        self.setup_tray()

    def window_flags(self):
        return (
            Qt.FramelessWindowHint
            | Qt.Tool                       # tidak muncul di taskbar
            | (Qt.WindowStaysOnTopHint if self.on_top        # di depan semua window
               else Qt.WindowStaysOnBottomHint)              # di bawah window lain, di atas wallpaper
            | Qt.WindowDoesNotAcceptFocus
        )

    # ---------- tray ----------
    def setup_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self)
        self.tray.setToolTip(APP_NAME)
        self.tray_menu = self.build_menu(None)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.on_tray)
        self.tray.show()

    def on_tray(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_visible()

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def build_menu(self, parent):
        m = QMenu(parent)
        m.addAction(APP_NAME).setEnabled(False)
        m.addSeparator()
        m.addAction(tr("menu.toggle")).triggered.connect(self.toggle_visible)
        lock = QAction(tr("menu.lock"), m, checkable=True, checked=self.locked)
        lock.toggled.connect(self.set_locked)
        m.addAction(lock)
        top = QAction(tr("menu.top"), m, checkable=True, checked=self.on_top)
        top.toggled.connect(self.set_on_top)
        m.addAction(top)
        bg = QAction(tr("menu.bg"), m, checkable=True, checked=self.show_bg)
        bg.toggled.connect(self.set_show_bg)
        m.addAction(bg)
        op = m.addMenu(tr("menu.opacity"))
        op.setEnabled(self.show_bg)
        for key, val in (("op.light", 90), ("op.medium", 140), ("op.solid", 220)):
            op.addAction(tr(key)).triggered.connect(lambda _, v=val: self.set_opacity(v))
        sv = m.addMenu(tr("menu.services"))
        for name, _, _, _ in SERVICES:
            sub = sv.addMenu(name)
            show = QAction(tr("menu.show"), sub, checkable=True, checked=self.svc[name]["show"])
            show.toggled.connect(lambda v, n=name: self.set_service_show(n, v))
            sub.addAction(show)
            if "port" in self.svc[name]:
                sub.addAction(tr("menu.port", port=self.svc[name]["port"])).triggered.connect(
                    lambda _, n=name: self.ask_port(n))
        dk = QAction(tr("menu.docker"), sv, checkable=True, checked=self.svc["Docker"]["show"])
        dk.toggled.connect(lambda v: self.set_service_show("Docker", v))
        sv.addAction(dk)
        fx = QAction(tr("menu.fx"), m, checkable=True, checked=FX)
        fx.toggled.connect(self.set_fx)
        m.addAction(fx)
        th = m.addMenu(tr("menu.theme"))
        tg = QActionGroup(th)
        for name in THEMES:
            act = QAction(theme_label(name), th, checkable=True, checked=(name == self.theme))
            act.triggered.connect(lambda _, n=name: self.set_theme(n))
            tg.addAction(act)
            th.addAction(act)
        fm = m.addMenu(tr("menu.font"))
        fg = QActionGroup(fm)
        for name in FONTS:
            act = QAction(name, fm, checkable=True, checked=(name == self.font_name))
            act.triggered.connect(lambda _, n=name: self.set_font(n))
            fg.addAction(act)
            fm.addAction(act)
        lg = m.addMenu(tr("menu.lang"))
        lgroup = QActionGroup(lg)
        for code, label in LANGS.items():
            act = QAction(label, lg, checkable=True, checked=(code == LANG))
            act.triggered.connect(lambda _, c=code: self.set_lang(c))
            lgroup.addAction(act)
            lg.addAction(act)
        iv = m.addMenu(tr("menu.interval"))
        group = QActionGroup(iv)
        for secs, key in INTERVALS:
            act = QAction(tr(key), iv, checkable=True, checked=(secs == self.interval))
            act.triggered.connect(lambda _, v=secs: self.set_interval(v))
            group.addAction(act)
            iv.addAction(act)
        auto = QAction(tr("menu.autostart"), m, checkable=True, checked=autostart_enabled())
        auto.toggled.connect(set_autostart)
        m.addAction(auto)
        m.addSeparator()
        m.addAction(tr("menu.quit")).triggered.connect(QApplication.quit)
        return m

    # ---------- data ----------
    def tick(self):
        self.cpu_now = psutil.cpu_percent(percpu=True)
        for h, v in zip(self.cpu_hist, self.cpu_now):
            h.append(v)
        f = psutil.cpu_freq()
        self.freq = f.current if f else None
        self.mem = psutil.virtual_memory()
        self.swap = psutil.swap_memory()
        self.ram_hist.append(self.mem.percent)
        self.sensors = self.read_sensors()
        self.swaps = read_swaps()
        self.nvme = read_nvme_info()
        self.battery = read_battery()
        self.read_nvme_usage()
        self.read_net()
        avg = sum(self.cpu_now) / len(self.cpu_now)
        if hasattr(self, "tray"):
            self.tray.setToolTip(f"{APP_NAME}\nCPU {avg:.0f}%  ·  RAM {self.mem.percent:.0f}%")
        self.update()

    def read_net(self):
        self.iface, self.is_wifi = pick_iface()
        try:
            c = psutil.net_io_counters(pernic=True).get(self.iface)
        except Exception:
            c = None
        if c is None:
            self._net_prev = None
            self.net_rate = (0.0, 0.0)
            return
        now = time.monotonic()
        prev = self._net_prev
        if prev and prev[3] == self.iface:
            dt = max(now - prev[0], 1e-3)
            down = max(0.0, (c.bytes_recv - prev[1]) / dt)
            up = max(0.0, (c.bytes_sent - prev[2]) / dt)
            self.net_rate = (down, up)
            self.net_down.append(down)
            self.net_up.append(up)
        self._net_prev = (now, c.bytes_recv, c.bytes_sent, self.iface)

    def read_nvme_usage(self):
        parts = []
        for part in psutil.disk_partitions():
            if part.device.startswith(f"/dev/{NVME_DEV}p"):
                try:
                    parts.append((part.mountpoint, psutil.disk_usage(part.mountpoint)))
                except OSError:
                    pass
        self.nvme_parts = parts
        try:
            c = psutil.disk_io_counters(perdisk=True)[NVME_DEV]
        except (KeyError, TypeError):
            self.nvme_io = None
            return
        now = time.monotonic()
        if self._io_prev:
            t0, r0, w0, b0 = self._io_prev
            dt = max(now - t0, 1e-3)
            busy = min(100.0, (c.busy_time - b0) / (dt * 10)) if hasattr(c, "busy_time") else 0.0
            self.nvme_io = ((c.read_bytes - r0) / dt, (c.write_bytes - w0) / dt, busy)
        self._io_prev = (now, c.read_bytes, c.write_bytes, getattr(c, "busy_time", 0))

    def read_sensors(self):
        rows = []
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
            temps = {}
        for chip, entries in temps.items():
            for e in entries:
                if not e.current:
                    continue
                label = e.label or chip
                name = f"{chip}/{label}" if chip != label else chip
                rows.append((name, f"{e.current:.0f}°C", temp_color(e.current, e.high or e.critical)))
        try:
            for chip, entries in psutil.sensors_fans().items():
                for e in entries:
                    rows.append((f"{chip}/{e.label or 'fan'}", f"{e.current} RPM", ACCENT))
        except Exception:
            pass
        return rows

    # ---------- painting ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.show_bg:
            bg = QPainterPath()
            bg.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 14, 14)
            a = self.opacity_bg
            if FX:
                grad = QLinearGradient(0, 0, 0, self.height())
                grad.setColorAt(0, alpha(BG_TOP, a))
                grad.setColorAt(1, alpha(BG_BOTTOM, a))
                p.fillPath(bg, QBrush(grad))
                edge = QLinearGradient(0, 0, 0, self.height())
                edge.setColorAt(0, alpha(TRACK, 70))
                edge.setColorAt(1, alpha(TRACK, 12))
                p.setPen(QPen(QBrush(edge), 1))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 14, 14)
            else:
                p.fillPath(bg, alpha(BG_BOTTOM, a))
            self.paint_content(p)
            return

        # Tanpa background: gambar konten ke layer transparan, beri bayangan tipis agar
        # tetap terbaca di atas wallpaper (QGraphicsEffect membuat window hitam di X11).
        r = self.devicePixelRatioF()
        layer = QImage(int(self.width() * r), int(self.height() * r), QImage.Format_ARGB32_Premultiplied)
        layer.setDevicePixelRatio(r)
        layer.fill(Qt.transparent)
        lp = QPainter(layer)
        lp.setRenderHint(QPainter.Antialiasing)
        self.paint_content(lp)
        lp.end()

        shadow = QImage(layer)
        sp = QPainter(shadow)
        sp.setCompositionMode(QPainter.CompositionMode_SourceIn)
        sp.fillRect(shadow.rect(), SHADOW)
        sp.end()
        for dx, dy in ((0, 1), (1, 1), (-1, 1), (0, 2), (1, 0), (-1, 0)):
            p.drawImage(dx, dy, shadow)
        p.drawImage(0, 0, layer)

    def paint_content(self, p):
        lx, colw = 16, COLW
        rx = lx + COLW + 24
        cx = rx + COLW + 24
        dx = cx + COLW + 24

        p.setFont(font(12, QFont.Bold))
        if FX:
            tg = QLinearGradient(44, 0, 230, 0)
            tg.setColorAt(0, TEXT)
            tg.setColorAt(1, ACCENT)
            p.setPen(QPen(QBrush(tg), 1))
        else:
            p.setPen(TEXT)
        p.drawPixmap(QRectF(14, 7, 26, 26), self.logo, QRectF(self.logo.rect()))
        p.drawText(QRectF(46, 8, self.width() - 62, 24), Qt.AlignLeft | Qt.AlignVCenter, APP_NAME)

        y = 40
        y = self.section(p, "CPU", self.cpu_title(), lx, y, colw)
        for i in range(self.ncpu):
            y = self.cpu_row(p, i, lx, y, colw)
        y += 6
        y = self.section(p, tr("sec.memory"), fmt_bytes(self.mem.used) + " / " + fmt_bytes(self.mem.total), lx, y, colw)
        y = self.ram_block(p, lx, y, colw)
        y += 6
        y = self.section(p, "SWAP", f"{fmt_bytes(self.swap.used)} / {fmt_bytes(self.swap.total)}", lx, y, colw)
        y = self.swap_block(p, lx, y, colw)
        y += 6
        y = self.section(p, tr("sec.network"), self.iface or tr("net.noconn"), lx, y, colw)
        self.network_block(p, lx, y, colw)

        y = 40
        y = self.section(p, tr("sec.services"), "", rx, y, colw)
        y = self.services_block(p, rx, y, colw)
        y += 6
        y = self.section(p, tr("sec.sensors"), "", rx, y, colw)
        self.sensor_block(p, rx, y, colw)

        y = 40
        y = self.section(p, "NVME", f"/dev/{NVME_DEV}", cx, y, colw)
        y = self.nvme_block(p, cx, y, colw)
        y += 6
        y = self.section(p, tr("sec.smart"), "", cx, y, colw)
        y = self.smart_block(p, cx, y, colw)
        if self.battery:
            y += 6
            y = self.section(p, tr("sec.battery"), self.battery["name"], cx, y, colw)
            y = self.battery_block(p, cx, y, colw)
        y += 6
        y = self.section(p, tr("sec.system"), "", cx, y, colw)
        self.system_block(p, cx, y, colw)

        if self.svc["Docker"]["show"]:
            self.docker_column(p, dx, colw)

        self.legend(p, 16, self.height() - 26, self.width() - 32)

    def cpu_title(self):
        avg = sum(self.cpu_now) / len(self.cpu_now)
        freq = f"  {self.freq / 1000:.2f} GHz" if self.freq else ""
        return f"{avg:.0f}%{freq}"

    def section(self, p, title, right, x, y, w):
        p.setFont(font(9, QFont.Bold))
        p.setPen(ACCENT)
        p.drawText(QRectF(x, y, w, 18), Qt.AlignLeft | Qt.AlignVCenter, title)
        p.setFont(font(9))
        p.setPen(MUTED)
        p.drawText(QRectF(x, y, w, 18), Qt.AlignRight | Qt.AlignVCenter, right)
        if FX:
            ln = QLinearGradient(x, 0, x + w, 0)
            ln.setColorAt(0, alpha(ACCENT, 170))
            ln.setColorAt(1, alpha(ACCENT, 0))
            p.setPen(QPen(QBrush(ln), 1.2))
        else:
            p.setPen(QPen(alpha(TRACK, 30), 1))
        p.drawLine(x, y + 21, x + w, y + 21)
        return y + 28

    def graph(self, p, rect, data, color):
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(alpha(TRACK, 14))
        p.drawRoundedRect(rect, 4, 4)
        pts = list(data)
        n = len(pts)
        step = rect.width() / (HISTORY - 1)
        x0 = rect.right() - step * (n - 1)
        path = QPainterPath()
        path.moveTo(x0, rect.bottom())
        for i, v in enumerate(pts):
            path.lineTo(x0 + i * step, rect.bottom() - rect.height() * min(v, 100) / 100)
        line = QPainterPath(path)
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()
        if FX:
            fill = QLinearGradient(0, rect.top(), 0, rect.bottom())
            fill.setColorAt(0, alpha(color, 130))
            fill.setColorAt(1, alpha(color, 8))
            p.fillPath(path, QBrush(fill))
        else:
            p.fillPath(path, alpha(color, 60))
        p.setBrush(Qt.NoBrush)
        # garis tanpa penutup
        line_only = QPainterPath()
        for i, v in enumerate(pts):
            pt = QPointF(x0 + i * step, rect.bottom() - rect.height() * min(v, 100) / 100)
            line_only.moveTo(pt) if i == 0 else line_only.lineTo(pt)
        if FX:
            p.setPen(QPen(alpha(color, 45), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(line_only)
        p.setPen(QPen(color, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(line_only)
        p.restore()

    def cpu_row(self, p, i, x, y, w):
        pct = self.cpu_now[i]
        col = level_color(pct)
        p.setFont(font(9))
        p.setPen(TEXT)
        p.drawText(QRectF(x, y, 46, 20), Qt.AlignLeft | Qt.AlignVCenter, f"Core {i}")
        self.graph(p, QRectF(x + 50, y, w - 50 - 48, 34), self.cpu_hist[i], col)
        p.setFont(font(11, QFont.Bold))
        p.setPen(col)
        p.drawText(QRectF(x + w - 44, y, 44, 34), Qt.AlignRight | Qt.AlignVCenter, f"{pct:.0f}%")
        return y + 42

    def bar(self, p, rect, pct, color):
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(alpha(TRACK, 22))
        p.drawRoundedRect(rect, 4, 4)
        fill = QRectF(rect.x(), rect.y(), rect.width() * min(pct, 100) / 100, rect.height())
        if FX and fill.width() > 1:
            p.setBrush(alpha(color, 55))
            p.drawRoundedRect(fill.adjusted(-1.5, -1.5, 1.5, 1.5), 5, 5)
            grad = QLinearGradient(fill.left(), 0, fill.right(), 0)
            grad.setColorAt(0, color.darker(150))
            grad.setColorAt(1, color)
            p.setBrush(QBrush(grad))
        else:
            p.setBrush(color)
        p.drawRoundedRect(fill, 4, 4)
        p.restore()

    def ram_block(self, p, x, y, w):
        pct = self.mem.percent
        col = level_color(pct)
        self.graph(p, QRectF(x, y, w - 52, 44), self.ram_hist, col)
        p.setFont(font(13, QFont.Bold))
        p.setPen(col)
        p.drawText(QRectF(x + w - 48, y, 48, 44), Qt.AlignRight | Qt.AlignVCenter, f"{pct:.0f}%")
        y += 52

        p.setFont(font(9))
        p.setPen(MUTED)
        p.drawText(QRectF(x, y, w, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   tr("mem.avail", size=fmt_bytes(self.mem.available)))
        return y + 20

    def dot_row(self, p, x, y, w, col, name, value, value_w=110):
        glow_dot(p, x + 4, y + 9, 3.5, col)
        p.setPen(TEXT)
        p.drawText(QRectF(x + 14, y, w - value_w - 14, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(name, Qt.ElideRight, int(w - value_w - 18)))
        p.setPen(col)
        p.drawText(QRectF(x + w - value_w, y, value_w, 18), Qt.AlignRight | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(value, Qt.ElideRight, int(value_w)))

    def usage_row(self, p, x, y, w, name, pct, text):
        col = level_color(pct)
        p.setFont(font(9))
        p.setPen(TEXT)
        p.drawText(QRectF(x, y, 62, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(name, Qt.ElideRight, 58))
        self.bar(p, QRectF(x + 66, y + 4, w - 66 - 138, 8), pct, col)
        p.setPen(col)
        p.drawText(QRectF(x + w - 134, y, 134, 16), Qt.AlignRight | Qt.AlignVCenter, text)
        return y + 22

    def swap_block(self, p, x, y, w):
        if not self.swaps:
            p.setFont(font(9))
            p.setPen(MUTED)
            p.drawText(QRectF(x, y, w, 18), Qt.AlignLeft | Qt.AlignVCenter, tr("swap.off"))
            return y + 22
        for name, kind, size, used in self.swaps:
            label = os.path.basename(name)
            pct = used / size * 100 if size else 0
            y = self.usage_row(p, x, y, w, label, pct, f"{fmt_bytes(used)} / {fmt_bytes(size)}")
        return y

    def speed_row(self, p, x, y, w, arrow, rate, hist, color):
        peak = max(max(hist), 10_000)   # skala minimum 10 KB/s agar noise kecil tidak membesar
        norm = [v / peak * 100 for v in hist]
        p.setFont(font(9, QFont.Bold))
        p.setPen(color)
        p.drawText(QRectF(x, y, 86, 26), Qt.AlignLeft | Qt.AlignVCenter, f"{arrow} {fmt_rate(rate)}")
        self.graph(p, QRectF(x + 92, y, w - 92, 26), norm, color)
        return y + 32

    def network_block(self, p, x, y, w):
        p.setFont(font(9))
        net = self.poller.data.get("Internet")
        if net is None:
            col, text = MUTED, tr("checking")
        elif not net["up"]:
            col, text = CRIT, tr("net.offline")
        else:
            col = WARN if net["ms"] >= 150 else OK
            text = tr("net.online", ms=f"{net['ms']:.0f}")
        self.dot_row(p, x, y, w, col, "Internet", text, 150)
        y += 19
        if self.is_wifi:
            wifi = self.poller.data.get("WiFi")
            if wifi:
                sig = wifi["signal"]
                col = MUTED if sig is None else OK if sig >= 60 else WARN if sig >= 35 else CRIT
                self.dot_row(p, x, y, w, col, f"WiFi: {wifi['ssid']}",
                             "—" if sig is None else tr("wifi.signal", sig=sig), 100)
            else:
                self.dot_row(p, x, y, w, CRIT, "WiFi", tr("wifi.disc"), 130)
            y += 19
        y += 4
        y = self.speed_row(p, x, y, w, "↓", self.net_rate[0], self.net_down, ACCENT)
        return self.speed_row(p, x, y, w, "↑", self.net_rate[1], self.net_up, UPLOAD)

    def container_state(self, c):
        state, status = c.get("State", ""), c.get("Status", "")
        if "unhealthy" in status or state == "dead":
            return CRIT
        if state == "running":
            return OK
        if state in ("paused", "restarting"):
            return WARN
        if state == "exited" and "Exited (0)" not in status:
            return CRIT
        return MUTED

    def docker_message(self, p, x, y, w, text, col=MUTED):
        p.setFont(font(9))
        p.setPen(col)
        p.drawText(QRectF(x, y, w, 18), Qt.AlignLeft | Qt.AlignVCenter, text)
        return y + 22

    def docker_column(self, p, x, w):
        dk = self.poller.data.get("Docker")
        y = 40
        if dk is None or "error" in dk:
            y = self.section(p, tr("sec.containers"), "", x, y, w)
            y = self.docker_message(p, x, y, w, tr("checking") if dk is None else tr(dk["error"]),
                                    MUTED if dk is None else CRIT)
            y += 6
            self.section(p, tr("sec.images"), "", x, y, w)
            return

        conts = sorted(dk["containers"], key=lambda c: (c.get("State") != "running", c["Names"][0]))
        running = sum(1 for c in conts if c.get("State") == "running")
        y = self.section(p, tr("sec.containers"), tr("dk.summary", n=running, t=len(conts), v=dk["version"]), x, y, w)
        p.setFont(font(9))
        if not conts:
            y = self.docker_message(p, x, y, w, tr("dk.nocont"))
        for c in conts[:DOCKER_MAX_ROWS]:
            self.dot_row(p, x, y, w, self.container_state(c), c["Names"][0].lstrip("/"), c.get("Status", ""), 130)
            y += 19
        if len(conts) > DOCKER_MAX_ROWS:
            y = self.docker_message(p, x, y, w, tr("more", n=len(conts) - DOCKER_MAX_ROWS))

        imgs = sorted(dk["images"], key=lambda i: -i.get("Size", 0))
        y += 6
        y = self.section(p, tr("sec.images"), tr("dk.images", n=len(imgs), size=fmt_bytes(sum(i.get("Size", 0) for i in imgs))), x, y, w)
        p.setFont(font(9))
        if not imgs:
            y = self.docker_message(p, x, y, w, tr("dk.noimg"))
        for img in imgs[:DOCKER_MAX_ROWS]:
            tags = img.get("RepoTags") or ["<none>"]
            col = OK if img["Id"] in dk["used"] else MUTED
            self.dot_row(p, x, y, w, col, tags[0], fmt_bytes(img.get("Size", 0)), 70)
            y += 19
        if len(imgs) > DOCKER_MAX_ROWS:
            self.docker_message(p, x, y, w, tr("more", n=len(imgs) - DOCKER_MAX_ROWS))

    def service_detail(self, info):
        if "policy" in info:
            text = tr("ufw.policy", i=info["policy"][0], o=info["policy"][1])
            return text + (tr("ufw.rules", n=info["rules"]) if info["rules"] is not None else "")
        return f"{info['version']} · {info['procs']} proc · {fmt_bytes(info['rss'])} · {info['ms']:.0f} ms"

    def services_block(self, p, x, y, w):
        p.setFont(font(9))
        names = [n for n, _, _, _ in SERVICES if self.svc[n]["show"]
                 and not (self.poller.data.get(n) or {}).get("absent")]
        if not names:
            return self.docker_message(p, x, y, w, tr("svc.none"))
        for name in names:
            info = self.poller.data.get(name)
            if info is None:
                col, status, detail = MUTED, tr("checking"), ""
            elif not info["up"]:
                col, status = CRIT, tr(info.get("down_key", "svc.down"))
                detail = self.service_detail(info) if "policy" in info else tr("svc.noresp")
            else:
                col = WARN if info["ms"] >= 200 else OK
                status, detail = tr(info.get("up_key", "svc.running")), self.service_detail(info)
            self.dot_row(p, x, y, w, col, name, status, 90)
            p.setPen(MUTED)
            p.setFont(font(8))
            p.drawText(QRectF(x + 14, y + 17, w - 14, 14), Qt.AlignLeft | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(detail, Qt.ElideRight, int(w - 14)))
            p.setFont(font(9))
            y += 38
        return y

    def nvme_block(self, p, x, y, w):
        n = self.nvme
        p.setFont(font(9))
        state_col = OK if n["state"] == "live" else CRIT
        self.dot_row(p, x, y, w, state_col, "Status", n["state"], 150)
        y += 19
        sm = self.smart.data or {}
        model = sm.get("model") or n["model"]
        fw = sm.get("fw") or n["fw"]
        self.dot_row(p, x, y, w, ACCENT, tr("nvme.model"), model, w - 70)
        y += 19
        p.setPen(MUTED)
        p.drawText(QRectF(x + 14, y, w - 14, 16), Qt.AlignLeft | Qt.AlignVCenter, f"firmware {fw}" if fw else "")
        y += 19
        if n["temp"] is not None:
            self.dot_row(p, x, y, w, temp_color(n["temp"], n["high"]), tr("nvme.temp"), f"{n['temp']:.0f}°C", 110)
            y += 19
        if self.nvme_io:
            r, wr, busy = self.nvme_io
            self.dot_row(p, x, y, w, level_color(busy), "I/O",
                         f"R {r / 1e6:.1f}  W {wr / 1e6:.1f} MB/s · {busy:.0f}%", 190)
            y += 19
        y += 3
        for mount, u in self.nvme_parts:
            y = self.usage_row(p, x, y, w, mount, u.percent, f"{fmt_bytes(u.used)} / {fmt_bytes(u.total)}")
        return y

    def smart_block(self, p, x, y, w):
        p.setFont(font(9))
        sm = self.smart.data
        if sm is None:
            return self.docker_message(p, x, y, w, tr("checking"))
        if "error" in sm:
            y = self.docker_message(p, x, y, w, tr(sm["error"]), CRIT if sm["error"] != "smart.missing" else WARN)
            hint = sm["error"] + ".hint"
            return self.docker_message(p, x, y, w, tr(hint)) if hint in I18N else y
        bad = not sm["passed"] or sm["crit"]
        spare, thr = sm["spare"], sm["spare_thr"] or 0
        used = sm["used"] or 0
        health_col = CRIT if bad else WARN if (spare is not None and spare <= max(thr, 50)) or used >= 80 else OK
        self.dot_row(p, x, y, w, health_col, tr("smart.health"),
                     ("PASSED" if sm["passed"] else "FAILED") + (f" · 0x{sm['crit']:02x}" if sm["crit"] else ""), 130)
        y += 19
        if spare is not None:
            self.dot_row(p, x, y, w, CRIT if spare <= thr else WARN if spare <= 50 else OK, tr("smart.spare"),
                         f"{spare}% (min {thr}%)", 130)
            y += 19
        y = self.usage_row(p, x, y, w, tr("smart.wear"), used, f"{used}%")
        self.dot_row(p, x, y, w, ACCENT, tr("smart.rw"), f"{fmt_tb(sm['written'])} / {fmt_tb(sm['read'])}", 150)
        y += 19
        if sm["hours"] is not None:
            self.dot_row(p, x, y, w, ACCENT, tr("smart.poh"),
                         tr("smart.poh.val", h=f"{sm['hours']:,}", d=sm["hours"] // 24), 150)
            y += 19
        if sm["cycles"] is not None:
            self.dot_row(p, x, y, w, ACCENT, tr("smart.cyc"), f"{sm['cycles']:,} · {sm['unsafe'] or 0:,}", 110)
            y += 19
        if sm["media"]:
            self.dot_row(p, x, y, w, CRIT, tr("smart.media"), str(sm["media"]), 110)
            y += 19
        return y

    def battery_block(self, p, x, y, w):
        b = self.battery
        p.setFont(font(9))
        cap = b["capacity"]
        if cap is not None:
            state = {"Charging": tr("bat.charging"), "Discharging": tr("bat.discharging"), "Full": tr("bat.full")}.get(
                b["status"], b["status"].lower())
            self.dot_row(p, x, y, w, CRIT if cap < 15 else WARN if cap < 35 else OK, tr("bat.cap"), f"{cap}% · {state}", 170)
            y += 19
        if b["health"] is not None:
            wh = f" ({b['full_wh']:.1f}/{b['design_wh']:.1f} Wh)" if b["full_wh"] and b["design_wh"] else ""
            h = b["health"]
            self.dot_row(p, x, y, w, CRIT if h < 60 else WARN if h < 80 else OK, tr("bat.health"), f"{h:.0f}%{wh}", 190)
            y += 19
        if b["cycles"] is not None:
            self.dot_row(p, x, y, w, ACCENT, tr("bat.cycles"), f"{b['cycles']:,}", 110)
            y += 19
        if b["watts"]:
            self.dot_row(p, x, y, w, ACCENT, tr("bat.power"), f"{b['watts']:.1f} W", 110)
            y += 19
        detail = " · ".join(v for v in (b["model"], b["tech"]) if v)
        if detail:
            p.setPen(MUTED)
            p.drawText(QRectF(x + 14, y, w - 14, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(detail, Qt.ElideRight, int(w - 14)))
            y += 19
        return y

    def system_block(self, p, x, y, w):
        p.setFont(font(9))
        t = self.install_time
        self.dot_row(p, x, y, w, ACCENT, tr("sys.age"), fmt_age(t) if t else tr("sys.unknown"), 150)
        y += 19
        p.setPen(MUTED)
        detail = " · ".join(v for v in (tr("sys.since", date=t.strftime("%Y-%m-%d")) if t else "", self.os_name) if v)
        p.drawText(QRectF(x + 14, y, w - 14, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(detail, Qt.ElideRight, int(w - 14)))
        return y + 19

    def sensor_block(self, p, x, y, w):
        p.setFont(font(9))
        limit = self.height() - 34
        if not self.sensors:
            p.setPen(MUTED)
            p.drawText(QRectF(x, y, w, 18), Qt.AlignLeft | Qt.AlignVCenter, tr("sensors.none"))
            return
        for name, val, col in self.sensors:
            if y + 18 > limit:
                break
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawEllipse(QPointF(x + 4, y + 9), 3.5, 3.5)
            p.setPen(TEXT)
            p.drawText(QRectF(x + 14, y, w - 124, 18), Qt.AlignLeft | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(name, Qt.ElideRight, int(w - 128)))
            p.setPen(col)
            p.drawText(QRectF(x + w - 110, y, 110, 18), Qt.AlignRight | Qt.AlignVCenter, val)
            y += 19

    def legend(self, p, x, y, w):
        p.setPen(QPen(alpha(TRACK, 30), 1))
        p.drawLine(x, y, x + w, y)
        p.setFont(font(8))
        items = ((OK, tr("legend.ok")), (WARN, tr("legend.warn")), (CRIT, tr("legend.crit")))
        cell = w / 3
        for i, (col, label) in enumerate(items):
            cx = x + i * cell
            glow_dot(p, cx + 5, y + 13, 4, col)
            p.setPen(MUTED)
            p.drawText(QRectF(cx + 14, y + 4, cell - 14, 18), Qt.AlignLeft | Qt.AlignVCenter, label)

    # ---------- interaksi ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.locked:
            self.drag = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self.drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self.drag)

    def mouseReleaseEvent(self, e):
        if self.drag is not None:
            self.drag = None
            self.persist()

    def persist(self):
        self.cfg.update(x=self.x(), y=self.y(), opacity=self.opacity_bg, show_bg=self.show_bg, fx=FX, lang=LANG, services=self.svc, theme=self.theme, font=self.font_name, locked=self.locked, on_top=self.on_top,
                        interval=self.interval)
        save_config(self.cfg)
        if hasattr(self, "tray"):   # sinkronkan centang menu tray
            QTimer.singleShot(0, self.refresh_tray_menu)

    def contextMenuEvent(self, e):
        self.build_menu(self).exec_(e.globalPos())

    def desired_width(self):
        return W if self.svc["Docker"]["show"] else W2

    def set_service_show(self, name, v):
        self.svc[name]["show"] = v
        if name == "Docker":
            self.resize(self.desired_width(), H)
        self.poller.wake.set()
        self.persist()
        self.update()

    def ask_port(self, name):
        port, ok = QInputDialog.getInt(None, tr("dlg.port_title", name=name), tr("dlg.port_label", name=name),
                                       self.svc[name]["port"], 1, 65535)
        if ok:
            self.svc[name]["port"] = port
            self.poller.data.pop(name, None)
            self.poller.wake.set()
            self.persist()
            self.update()

    def set_interval(self, secs):
        self.interval = secs
        self.timer.start(secs * 1000)
        self.poller.interval = max(MIN_SERVICE_INTERVAL, secs)
        self.persist()
        self.tick()

    def refresh_tray_menu(self):
        self.tray_menu = self.build_menu(None)
        self.tray.setContextMenu(self.tray_menu)

    def set_locked(self, v):
        self.locked = v
        self.persist()

    def set_on_top(self, v):
        self.on_top = v
        visible = self.isVisible()
        self.setWindowFlags(self.window_flags())   # mengganti flag menyembunyikan window
        if visible:
            self.show()
        self.persist()

    def set_fx(self, v):
        global FX
        FX = v
        self.persist()
        self.update()

    def fade_in(self):
        self.setWindowOpacity(0.0)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(700)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def set_lang(self, code):
        global LANG
        LANG = code
        self.sensors = self.read_sensors()   # nama baterai ikut bahasa
        self.persist()
        self.update()

    def set_theme(self, name):
        self.theme = name
        apply_theme(name)
        self.sensors = self.read_sensors()   # warna status ikut tema
        self.persist()
        self.update()

    def set_font(self, name):
        global FONT_FAMILY
        self.font_name = name
        FONT_FAMILY = FONTS[name]
        self.persist()
        self.update()

    def set_show_bg(self, v):
        self.show_bg = v
        self.persist()
        self.update()

    def set_opacity(self, v):
        self.opacity_bg = v
        self.persist()
        self.update()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)   # tetap hidup di tray

    lock = QLockFile(QDir.tempPath() + f"/system-monitoring-{os.getuid()}.lock")
    if not lock.tryLock(0):                # sudah berjalan
        sys.exit(0)

    w = Widget()
    w.show()
    w.fade_in()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
